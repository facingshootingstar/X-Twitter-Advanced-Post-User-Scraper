"""
scraper.py — Core scraping engine for X (Twitter) Advanced Scraper.

Provides three scraping strategies:
  1. TwitterAPIScraper  — Twitter API v2 via tweepy (primary)
  2. BrowserScraper     — Playwright headless fallback
  3. XScraper           — Unified façade combining both

All scrapers return normalised dicts ready for export.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, Optional

import tweepy
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from tweepy.errors import TooManyRequests, TwitterServerError

from config import get_settings
from utils.helpers import (
    build_query,
    clean_text,
    dedup_by_key,
    extract_hashtags,
    extract_mentions,
    extract_urls,
    iso_now,
    parse_twitter_date,
    smart_delay,
    sync_delay,
)

# ---------------------------------------------------------------------------
# Tweet / User field expansions for API v2
# ---------------------------------------------------------------------------
TWEET_FIELDS = [
    "id",
    "text",
    "created_at",
    "author_id",
    "conversation_id",
    "in_reply_to_user_id",
    "public_metrics",
    "entities",
    "attachments",
    "lang",
    "source",
    "referenced_tweets",
    "geo",
]

USER_FIELDS = [
    "id",
    "name",
    "username",
    "created_at",
    "description",
    "location",
    "public_metrics",
    "profile_image_url",
    "url",
    "verified",
    "verified_type",
    "pinned_tweet_id",
]

EXPANSIONS = [
    "author_id",
    "referenced_tweets.id",
    "referenced_tweets.id.author_id",
    "in_reply_to_user_id",
    "attachments.media_keys",
]

MEDIA_FIELDS = [
    "media_key",
    "type",
    "url",
    "preview_image_url",
    "alt_text",
    "public_metrics",
]


# ═══════════════════════════════════════════════════════════════════════════
# Twitter API v2 Scraper (Primary)
# ═══════════════════════════════════════════════════════════════════════════
class TwitterAPIScraper:
    """
    Scrapes X/Twitter using API v2 (via tweepy).

    Handles:
      • Tweet search (recent & full-archive with Academic access)
      • User profile lookup
      • User timeline (tweets + replies)
      • Followers / following lists
      • Hashtag & keyword search
      • Engagement metrics extraction
    """

    def __init__(self) -> None:
        cfg = get_settings()
        self.client = tweepy.Client(
            bearer_token=cfg.api.bearer_token,
            consumer_key=cfg.api.api_key or None,
            consumer_secret=cfg.api.api_secret or None,
            access_token=cfg.api.access_token or None,
            access_token_secret=cfg.api.access_secret or None,
            wait_on_rate_limit=True,
        )
        self._max = cfg.scraper.max_tweets
        self._min_delay = cfg.scraper.min_delay
        self._max_delay = cfg.scraper.max_delay
        logger.info("TwitterAPIScraper initialised (max_tweets={})", self._max)

    # ------------------------------------------------------------------
    # Internal: normalise a single tweet response into a flat dict
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_tweet(tweet: tweepy.Tweet, includes: dict | None = None) -> dict[str, Any]:
        """Flatten a tweepy Tweet object into a clean dict."""
        data: dict[str, Any] = {
            "id": str(tweet.id),
            "text": tweet.text,
            "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
            "author_id": str(tweet.author_id) if tweet.author_id else None,
            "conversation_id": str(tweet.conversation_id) if tweet.conversation_id else None,
            "in_reply_to_user_id": (
                str(tweet.in_reply_to_user_id) if tweet.in_reply_to_user_id else None
            ),
            "lang": tweet.lang if hasattr(tweet, "lang") else None,
            "source": tweet.source if hasattr(tweet, "source") else None,
        }

        # Public metrics
        pm = tweet.public_metrics or {}
        data["retweet_count"] = pm.get("retweet_count", 0)
        data["reply_count"] = pm.get("reply_count", 0)
        data["like_count"] = pm.get("like_count", 0)
        data["quote_count"] = pm.get("quote_count", 0)
        data["bookmark_count"] = pm.get("bookmark_count", 0)
        data["impression_count"] = pm.get("impression_count", 0)

        # Extracted entities
        data["hashtags"] = extract_hashtags(tweet.text)
        data["mentions"] = extract_mentions(tweet.text)
        data["urls"] = extract_urls(tweet.text)
        data["clean_text"] = clean_text(tweet.text, strip_urls=True, strip_mentions=True)

        # Referenced tweets (retweet / quote / reply)
        refs = tweet.referenced_tweets or []
        data["is_retweet"] = any(r.type == "retweeted" for r in refs)
        data["is_quote"] = any(r.type == "quoted" for r in refs)
        data["is_reply"] = tweet.in_reply_to_user_id is not None

        # Author info from includes
        if includes and "users" in includes:
            user_map = {str(u.id): u for u in includes["users"]}
            author = user_map.get(str(tweet.author_id))
            if author:
                data["author_username"] = author.username
                data["author_name"] = author.name
                data["author_followers"] = (
                    author.public_metrics.get("followers_count", 0)
                    if author.public_metrics
                    else 0
                )

        data["scraped_at"] = iso_now()
        return data

    @staticmethod
    def _normalise_user(user: tweepy.User) -> dict[str, Any]:
        """Flatten a tweepy User object into a clean dict."""
        pm = user.public_metrics or {}
        return {
            "id": str(user.id),
            "name": user.name,
            "username": user.username,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "description": user.description or "",
            "location": user.location or "",
            "url": user.url or "",
            "profile_image_url": user.profile_image_url or "",
            "verified": getattr(user, "verified", False),
            "verified_type": getattr(user, "verified_type", None),
            "followers_count": pm.get("followers_count", 0),
            "following_count": pm.get("following_count", 0),
            "tweet_count": pm.get("tweet_count", 0),
            "listed_count": pm.get("listed_count", 0),
            "scraped_at": iso_now(),
        }

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------
    @retry(
        retry=retry_if_exception_type((TooManyRequests, TwitterServerError)),
        wait=wait_exponential(multiplier=1, min=10, max=120),
        stop=stop_after_attempt(5),
        before_sleep=lambda rs: logger.warning(
            "Rate-limited — retrying in {:.0f}s (attempt {}/5)",
            rs.next_action.sleep,  # type: ignore[union-attr]
            rs.attempt_number,
        ),
    )
    def search_tweets(
        self,
        query: str,
        *,
        max_results: int | None = None,
        sort_order: str = "relevancy",
        since_id: str | None = None,
        until_id: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search recent tweets matching *query*.

        Uses pagination to collect up to ``max_results`` tweets.
        """
        limit = max_results or self._max
        logger.info("Searching tweets: query='{}', limit={}", query, limit)

        results: list[dict[str, Any]] = []

        for response in tweepy.Paginator(
            self.client.search_recent_tweets,
            query=query,
            max_results=min(100, limit),
            tweet_fields=TWEET_FIELDS,
            user_fields=USER_FIELDS,
            expansions=EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            sort_order=sort_order,
            since_id=since_id,
            until_id=until_id,
            start_time=start_time,
            end_time=end_time,
        ).flatten(limit=limit):
            results.append(self._normalise_tweet(response))
            if len(results) >= limit:
                break
            sync_delay(self._min_delay, self._max_delay)

        results = dedup_by_key(results, "id")
        logger.success("Collected {} tweets for query '{}'", len(results), query)
        return results

    def search_tweets_advanced(
        self,
        *,
        keywords: list[str] | None = None,
        from_user: str | None = None,
        to_user: str | None = None,
        hashtags: list[str] | None = None,
        lang: str | None = None,
        min_replies: int | None = None,
        min_retweets: int | None = None,
        min_likes: int | None = None,
        is_reply: bool | None = None,
        has_media: bool | None = None,
        since: str | None = None,
        until: str | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Build a query from structured params and search."""
        query = build_query(
            keywords=keywords,
            from_user=from_user,
            to_user=to_user,
            hashtags=hashtags,
            lang=lang,
            min_replies=min_replies,
            min_retweets=min_retweets,
            min_likes=min_likes,
            is_reply=is_reply,
            has_media=has_media,
            since=since,
            until=until,
        )
        return self.search_tweets(query, max_results=max_results)

    @retry(
        retry=retry_if_exception_type((TooManyRequests, TwitterServerError)),
        wait=wait_exponential(multiplier=1, min=10, max=120),
        stop=stop_after_attempt(5),
    )
    def get_user_tweets(
        self,
        username: str,
        *,
        max_results: int | None = None,
        include_replies: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch tweets from a specific user's timeline."""
        limit = max_results or self._max
        logger.info("Fetching tweets for @{} (limit={}, replies={})", username, limit, include_replies)

        # Resolve username → user ID
        user_resp = self.client.get_user(username=username, user_fields=USER_FIELDS)
        if not user_resp or not user_resp.data:
            logger.error("User @{} not found", username)
            return []

        user_id = user_resp.data.id
        exclude = [] if include_replies else ["replies", "retweets"]

        results: list[dict[str, Any]] = []
        for response in tweepy.Paginator(
            self.client.get_users_tweets,
            id=user_id,
            max_results=min(100, limit),
            tweet_fields=TWEET_FIELDS,
            user_fields=USER_FIELDS,
            expansions=EXPANSIONS,
            media_fields=MEDIA_FIELDS,
            exclude=exclude if exclude else None,
        ).flatten(limit=limit):
            results.append(self._normalise_tweet(response))
            if len(results) >= limit:
                break
            sync_delay(self._min_delay, self._max_delay)

        results = dedup_by_key(results, "id")
        logger.success("Collected {} tweets from @{}", len(results), username)
        return results

    @retry(
        retry=retry_if_exception_type((TooManyRequests, TwitterServerError)),
        wait=wait_exponential(multiplier=1, min=10, max=120),
        stop=stop_after_attempt(5),
    )
    def get_user_profile(self, username: str) -> dict[str, Any] | None:
        """Fetch a single user profile by username."""
        logger.info("Fetching profile for @{}", username)
        resp = self.client.get_user(username=username, user_fields=USER_FIELDS)
        if not resp or not resp.data:
            logger.error("User @{} not found", username)
            return None
        return self._normalise_user(resp.data)

    def get_user_profiles(self, usernames: list[str]) -> list[dict[str, Any]]:
        """Fetch profiles for a batch of usernames."""
        logger.info("Fetching {} user profiles", len(usernames))
        profiles: list[dict[str, Any]] = []
        # API allows up to 100 usernames per call
        for i in range(0, len(usernames), 100):
            batch = usernames[i : i + 100]
            resp = self.client.get_users(
                usernames=batch,
                user_fields=USER_FIELDS,
            )
            if resp and resp.data:
                for user in resp.data:
                    profiles.append(self._normalise_user(user))
            sync_delay(self._min_delay, self._max_delay)

        logger.success("Fetched {} user profiles", len(profiles))
        return profiles

    @retry(
        retry=retry_if_exception_type((TooManyRequests, TwitterServerError)),
        wait=wait_exponential(multiplier=1, min=10, max=120),
        stop=stop_after_attempt(5),
    )
    def get_user_followers(
        self,
        username: str,
        *,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch followers of a user."""
        limit = max_results or min(self._max, 1000)
        logger.info("Fetching followers for @{} (limit={})", username, limit)

        user_resp = self.client.get_user(username=username, user_fields=["id"])
        if not user_resp or not user_resp.data:
            logger.error("User @{} not found", username)
            return []

        user_id = user_resp.data.id
        followers: list[dict[str, Any]] = []

        for response in tweepy.Paginator(
            self.client.get_users_followers,
            id=user_id,
            max_results=min(1000, limit),
            user_fields=USER_FIELDS,
        ).flatten(limit=limit):
            followers.append(self._normalise_user(response))
            if len(followers) >= limit:
                break

        logger.success("Fetched {} followers of @{}", len(followers), username)
        return followers

    @retry(
        retry=retry_if_exception_type((TooManyRequests, TwitterServerError)),
        wait=wait_exponential(multiplier=1, min=10, max=120),
        stop=stop_after_attempt(5),
    )
    def get_user_following(
        self,
        username: str,
        *,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch accounts a user is following."""
        limit = max_results or min(self._max, 1000)
        logger.info("Fetching following for @{} (limit={})", username, limit)

        user_resp = self.client.get_user(username=username, user_fields=["id"])
        if not user_resp or not user_resp.data:
            logger.error("User @{} not found", username)
            return []

        user_id = user_resp.data.id
        following: list[dict[str, Any]] = []

        for response in tweepy.Paginator(
            self.client.get_users_following,
            id=user_id,
            max_results=min(1000, limit),
            user_fields=USER_FIELDS,
        ).flatten(limit=limit):
            following.append(self._normalise_user(response))
            if len(following) >= limit:
                break

        logger.success("Fetched {} following of @{}", len(following), username)
        return following

    def get_tweet_replies(
        self,
        tweet_id: str,
        *,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch replies to a specific tweet using conversation_id search."""
        limit = max_results or self._max
        query = f"conversation_id:{tweet_id} is:reply"
        logger.info("Fetching replies to tweet {} (limit={})", tweet_id, limit)
        return self.search_tweets(query, max_results=limit)

    def get_hashtag_tweets(
        self,
        hashtag: str,
        *,
        max_results: int | None = None,
        lang: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch tweets containing a specific hashtag."""
        tag = hashtag.lstrip("#")
        query = f"#{tag}"
        if lang:
            query += f" lang:{lang}"
        logger.info("Fetching tweets with #{} (limit={})", tag, max_results or self._max)
        return self.search_tweets(query, max_results=max_results)


# ═══════════════════════════════════════════════════════════════════════════
# Browser-based Scraper (Playwright fallback)
# ═══════════════════════════════════════════════════════════════════════════
class BrowserScraper:
    """
    Headless browser scraper using Playwright as a fallback when API
    access is limited or when scraping public pages without auth.

    Extracts tweet data from rendered DOM elements.
    """

    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._browser = None
        self._context = None
        self._page = None
        logger.info("BrowserScraper initialised (headless={})", headless)

    async def _launch(self) -> None:
        """Launch Playwright browser."""
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        self._page = await self._context.new_page()

        # Stealth: remove webdriver flag
        await self._page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
            """
        )
        logger.info("Playwright browser launched")

    async def _close(self) -> None:
        """Clean up Playwright resources."""
        if self._browser:
            await self._browser.close()
        if hasattr(self, "_pw") and self._pw:
            await self._pw.stop()
        logger.info("Playwright browser closed")

    async def scrape_user_tweets(
        self,
        username: str,
        *,
        max_tweets: int = 50,
        scroll_pause: float = 2.0,
    ) -> list[dict[str, Any]]:
        """
        Scrape tweets from a user's public profile page.

        Scrolls the page to load more tweets dynamically.
        """
        await self._launch()
        tweets: list[dict[str, Any]] = []

        try:
            url = f"https://x.com/{username}"
            logger.info("Navigating to {}", url)
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            scroll_count = 0
            max_scrolls = max_tweets // 5 + 10  # rough estimate

            while len(tweets) < max_tweets and scroll_count < max_scrolls:
                # Extract tweet articles from DOM
                articles = await self._page.query_selector_all('article[data-testid="tweet"]')

                for article in articles:
                    try:
                        tweet_data = await self._extract_tweet_from_dom(article)
                        if tweet_data and tweet_data["id"] not in {t["id"] for t in tweets}:
                            tweets.append(tweet_data)
                    except Exception as e:
                        logger.debug("Failed to extract tweet: {}", e)
                        continue

                # Scroll down
                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(scroll_pause)
                scroll_count += 1
                logger.debug(
                    "Scroll {}/{} — {} tweets collected",
                    scroll_count,
                    max_scrolls,
                    len(tweets),
                )

        except Exception as e:
            logger.error("Browser scraping failed: {}", e)
        finally:
            await self._close()

        return tweets[:max_tweets]

    async def _extract_tweet_from_dom(self, article) -> dict[str, Any] | None:
        """Extract tweet data from a DOM article element."""
        try:
            # Tweet text
            text_el = await article.query_selector('[data-testid="tweetText"]')
            text = await text_el.inner_text() if text_el else ""

            # Username
            user_el = await article.query_selector(
                'div[data-testid="User-Name"] a[role="link"]'
            )
            username = ""
            if user_el:
                href = await user_el.get_attribute("href") or ""
                username = href.strip("/").split("/")[-1] if href else ""

            # Timestamp
            time_el = await article.query_selector("time")
            created_at = ""
            if time_el:
                created_at = await time_el.get_attribute("datetime") or ""

            # Permalink for ID extraction
            link_el = await article.query_selector('a[href*="/status/"]')
            tweet_id = ""
            if link_el:
                href = await link_el.get_attribute("href") or ""
                match = re.search(r"/status/(\d+)", href)
                if match:
                    tweet_id = match.group(1)

            if not tweet_id:
                return None

            # Engagement metrics
            metrics = await self._extract_metrics(article)

            return {
                "id": tweet_id,
                "text": text,
                "clean_text": clean_text(text, strip_urls=True),
                "created_at": created_at,
                "author_username": username,
                "hashtags": extract_hashtags(text),
                "mentions": extract_mentions(text),
                "urls": extract_urls(text),
                "retweet_count": metrics.get("retweets", 0),
                "reply_count": metrics.get("replies", 0),
                "like_count": metrics.get("likes", 0),
                "view_count": metrics.get("views", 0),
                "is_retweet": False,
                "is_reply": False,
                "scraped_at": iso_now(),
                "source": "browser",
            }
        except Exception as e:
            logger.debug("DOM extraction error: {}", e)
            return None

    async def _extract_metrics(self, article) -> dict[str, int]:
        """Extract engagement metric counts from tweet article."""
        metrics: dict[str, int] = {
            "replies": 0,
            "retweets": 0,
            "likes": 0,
            "views": 0,
        }

        metric_groups = await article.query_selector_all('[role="group"] button')
        labels = ["replies", "retweets", "likes", "views"]

        for i, btn in enumerate(metric_groups):
            if i >= len(labels):
                break
            try:
                aria = await btn.get_attribute("aria-label") or ""
                nums = re.findall(r"[\d,]+", aria)
                if nums:
                    metrics[labels[i]] = int(nums[0].replace(",", ""))
            except Exception:
                continue

        return metrics

    async def scrape_search(
        self,
        query: str,
        *,
        max_tweets: int = 50,
    ) -> list[dict[str, Any]]:
        """Search tweets via X.com search page."""
        await self._launch()
        tweets: list[dict[str, Any]] = []

        try:
            import urllib.parse

            encoded = urllib.parse.quote(query)
            url = f"https://x.com/search?q={encoded}&src=typed_query&f=live"
            logger.info("Browser search: {}", url)
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            scroll_count = 0
            max_scrolls = max_tweets // 5 + 10

            while len(tweets) < max_tweets and scroll_count < max_scrolls:
                articles = await self._page.query_selector_all(
                    'article[data-testid="tweet"]'
                )
                for article in articles:
                    try:
                        tweet_data = await self._extract_tweet_from_dom(article)
                        if tweet_data and tweet_data["id"] not in {t["id"] for t in tweets}:
                            tweets.append(tweet_data)
                    except Exception:
                        continue

                await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
                await asyncio.sleep(2)
                scroll_count += 1

        except Exception as e:
            logger.error("Browser search failed: {}", e)
        finally:
            await self._close()

        return tweets[:max_tweets]


# ═══════════════════════════════════════════════════════════════════════════
# Unified Scraper Façade
# ═══════════════════════════════════════════════════════════════════════════
class XScraper:
    """
    High-level façade that orchestrates API and browser scrapers.

    Usage:
        scraper = XScraper()
        tweets = scraper.search("python AI", max_results=200)
        profile = scraper.user_profile("elonmusk")
    """

    def __init__(self) -> None:
        cfg = get_settings()
        self.api = TwitterAPIScraper()
        self._use_browser = cfg.scraper.use_browser_fallback
        self._headless = cfg.scraper.headless
        self._browser: BrowserScraper | None = None
        if self._use_browser:
            self._browser = BrowserScraper(headless=self._headless)
        logger.info("XScraper ready (browser_fallback={})", self._use_browser)

    def search(
        self,
        query: str,
        *,
        max_results: int | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """Search tweets — API first, browser fallback."""
        try:
            return self.api.search_tweets(query, max_results=max_results, **kwargs)
        except Exception as e:
            logger.warning("API search failed: {} — trying browser fallback", e)
            if self._browser:
                return asyncio.run(
                    self._browser.scrape_search(query, max_tweets=max_results or 50)
                )
            raise

    def advanced_search(self, **kwargs) -> list[dict[str, Any]]:
        """Structured advanced search with all filters."""
        return self.api.search_tweets_advanced(**kwargs)

    def user_tweets(
        self,
        username: str,
        *,
        max_results: int | None = None,
        include_replies: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch a user's tweets — API first, browser fallback."""
        try:
            return self.api.get_user_tweets(
                username, max_results=max_results, include_replies=include_replies
            )
        except Exception as e:
            logger.warning("API user_tweets failed: {} — trying browser", e)
            if self._browser:
                return asyncio.run(
                    self._browser.scrape_user_tweets(
                        username, max_tweets=max_results or 50
                    )
                )
            raise

    def user_profile(self, username: str) -> dict[str, Any] | None:
        """Fetch a user profile."""
        return self.api.get_user_profile(username)

    def user_profiles(self, usernames: list[str]) -> list[dict[str, Any]]:
        """Batch user profile lookup."""
        return self.api.get_user_profiles(usernames)

    def user_followers(self, username: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
        """Fetch user followers."""
        return self.api.get_user_followers(username, max_results=max_results)

    def user_following(self, username: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
        """Fetch accounts a user follows."""
        return self.api.get_user_following(username, max_results=max_results)

    def tweet_replies(self, tweet_id: str, *, max_results: int | None = None) -> list[dict[str, Any]]:
        """Fetch replies to a tweet."""
        return self.api.get_tweet_replies(tweet_id, max_results=max_results)

    def hashtag_tweets(
        self,
        hashtag: str,
        *,
        max_results: int | None = None,
        lang: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch tweets for a hashtag."""
        return self.api.get_hashtag_tweets(hashtag, max_results=max_results, lang=lang)
