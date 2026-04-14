"""
main.py — CLI entry point for X (Twitter) Advanced Post & User Scraper.

Provides a rich Click-based CLI with commands for every scraping operation.

Usage:
    python main.py search "python AI" --max 200 --format csv
    python main.py user-tweets elonmusk --max 100
    python main.py user-profile elonmusk
    python main.py hashtag python --lang en --max 300
    python main.py followers elonmusk --max 500
    python main.py replies 1234567890 --max 100
    python main.py advanced --keywords "AI,ML" --from-user openai --lang en
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from config import get_settings
from scraper import XScraper
from utils.helpers import export_data, preview_table, setup_logging

console = Console()

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
BANNER = r"""
██╗  ██╗    ███████╗ ██████╗██████╗  █████╗ ██████╗ ███████╗██████╗
╚██╗██╔╝    ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
 ╚███╔╝     ███████╗██║     ██████╔╝███████║██████╔╝█████╗  ██████╔╝
 ██╔██╗     ╚════██║██║     ██╔══██╗██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗
██╔╝ ██╗    ███████║╚██████╗██║  ██║██║  ██║██║     ███████╗██║  ██║
╚═╝  ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝
"""


def show_banner() -> None:
    """Display the startup banner."""
    banner_text = Text(BANNER, style="bold cyan")
    panel = Panel(
        banner_text,
        title="[bold white]X (Twitter) Advanced Scraper[/bold white]",
        subtitle="[dim]v1.0.0 — Production Ready[/dim]",
        border_style="bright_blue",
        padding=(0, 2),
    )
    console.print(panel)
    console.print()


# ---------------------------------------------------------------------------
# Click CLI Group
# ---------------------------------------------------------------------------
@click.group(invoke_without_command=True)
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.pass_context
def cli(ctx: click.Context, debug: bool) -> None:
    """X (Twitter) Advanced Post & User Scraper — CLI."""
    cfg = get_settings()
    level = "DEBUG" if debug else cfg.log.log_level
    setup_logging(log_level=level, log_file=cfg.log.log_file)

    show_banner()

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# Common options
# ---------------------------------------------------------------------------
def common_options(func):
    """Shared CLI options for output format and limit."""
    func = click.option(
        "--max", "max_results", default=None, type=int, help="Maximum results to fetch."
    )(func)
    func = click.option(
        "--format",
        "fmt",
        default=None,
        type=click.Choice(["csv", "json", "excel"]),
        help="Output format (overrides .env).",
    )(func)
    func = click.option(
        "--output-dir",
        default=None,
        type=click.Path(),
        help="Output directory (overrides .env).",
    )(func)
    func = click.option(
        "--preview/--no-preview",
        default=True,
        help="Show Rich table preview.",
    )(func)
    return func


def _resolve_output(fmt: str | None, output_dir: str | None) -> tuple[str, Path]:
    """Resolve output format and dir from CLI args or config."""
    cfg = get_settings()
    resolved_fmt = fmt or cfg.scraper.output_format
    resolved_dir = Path(output_dir) if output_dir else cfg.scraper.output_dir
    return resolved_fmt, resolved_dir


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("query")
@common_options
@click.option("--sort", "sort_order", default="relevancy", type=click.Choice(["relevancy", "recency"]))
def search(query: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool, sort_order: str) -> None:
    """Search tweets by keyword or query string."""
    console.print(f"[bold green]🔍 Searching tweets:[/bold green] [yellow]{query}[/yellow]")

    scraper = XScraper()
    tweets = scraper.search(query, max_results=max_results, sort_order=sort_order)

    if not tweets:
        console.print("[red]No tweets found.[/red]")
        return

    if preview:
        preview_table(tweets, title=f"Tweets for: {query}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(tweets, filename=f"search_{query[:30].replace(' ', '_')}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(tweets)} tweets → {path}[/bold green]")


@cli.command("user-tweets")
@click.argument("username")
@common_options
@click.option("--replies/--no-replies", default=False, help="Include replies.")
def user_tweets(username: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool, replies: bool) -> None:
    """Fetch tweets from a user's timeline."""
    console.print(f"[bold green]👤 Fetching tweets from:[/bold green] [yellow]@{username}[/yellow]")

    scraper = XScraper()
    tweets = scraper.user_tweets(username, max_results=max_results, include_replies=replies)

    if not tweets:
        console.print("[red]No tweets found.[/red]")
        return

    if preview:
        preview_table(tweets, title=f"Tweets by @{username}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(tweets, filename=f"user_{username}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(tweets)} tweets → {path}[/bold green]")


@cli.command("user-profile")
@click.argument("username")
@common_options
def user_profile(username: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool) -> None:
    """Fetch a user's profile information."""
    console.print(f"[bold green]📋 Fetching profile:[/bold green] [yellow]@{username}[/yellow]")

    scraper = XScraper()
    profile = scraper.user_profile(username)

    if not profile:
        console.print("[red]User not found.[/red]")
        return

    if preview:
        preview_table([profile], title=f"Profile: @{username}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data([profile], filename=f"profile_{username}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved profile → {path}[/bold green]")


@cli.command("user-profiles")
@click.argument("usernames", nargs=-1, required=True)
@common_options
def user_profiles(usernames: tuple[str, ...], max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool) -> None:
    """Fetch profiles for multiple users (space-separated)."""
    console.print(f"[bold green]📋 Fetching {len(usernames)} profiles[/bold green]")

    scraper = XScraper()
    profiles = scraper.user_profiles(list(usernames))

    if not profiles:
        console.print("[red]No profiles found.[/red]")
        return

    if preview:
        preview_table(profiles, title="User Profiles")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(profiles, filename="profiles_batch", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(profiles)} profiles → {path}[/bold green]")


@cli.command()
@click.argument("hashtag")
@common_options
@click.option("--lang", default=None, help="Language filter (e.g. 'en').")
def hashtag(hashtag: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool, lang: str | None) -> None:
    """Fetch tweets by hashtag."""
    tag = hashtag.lstrip("#")
    console.print(f"[bold green]#️⃣ Fetching tweets for:[/bold green] [yellow]#{tag}[/yellow]")

    scraper = XScraper()
    tweets = scraper.hashtag_tweets(tag, max_results=max_results, lang=lang)

    if not tweets:
        console.print("[red]No tweets found.[/red]")
        return

    if preview:
        preview_table(tweets, title=f"Tweets with #{tag}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(tweets, filename=f"hashtag_{tag}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(tweets)} tweets → {path}[/bold green]")


@cli.command()
@click.argument("username")
@common_options
def followers(username: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool) -> None:
    """Fetch a user's followers."""
    console.print(f"[bold green]👥 Fetching followers of:[/bold green] [yellow]@{username}[/yellow]")

    scraper = XScraper()
    data = scraper.user_followers(username, max_results=max_results)

    if not data:
        console.print("[red]No followers found.[/red]")
        return

    if preview:
        preview_table(data, title=f"Followers of @{username}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(data, filename=f"followers_{username}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(data)} followers → {path}[/bold green]")


@cli.command()
@click.argument("username")
@common_options
def following(username: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool) -> None:
    """Fetch accounts a user is following."""
    console.print(f"[bold green]👥 Fetching following of:[/bold green] [yellow]@{username}[/yellow]")

    scraper = XScraper()
    data = scraper.user_following(username, max_results=max_results)

    if not data:
        console.print("[red]No following found.[/red]")
        return

    if preview:
        preview_table(data, title=f"Following by @{username}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(data, filename=f"following_{username}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(data)} following → {path}[/bold green]")


@cli.command()
@click.argument("tweet_id")
@common_options
def replies(tweet_id: str, max_results: int | None, fmt: str | None, output_dir: str | None, preview: bool) -> None:
    """Fetch replies to a specific tweet."""
    console.print(f"[bold green]💬 Fetching replies to:[/bold green] [yellow]{tweet_id}[/yellow]")

    scraper = XScraper()
    data = scraper.tweet_replies(tweet_id, max_results=max_results)

    if not data:
        console.print("[red]No replies found.[/red]")
        return

    if preview:
        preview_table(data, title=f"Replies to tweet {tweet_id}")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(data, filename=f"replies_{tweet_id}", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(data)} replies → {path}[/bold green]")


@cli.command()
@common_options
@click.option("--keywords", default=None, help="Comma-separated keywords.")
@click.option("--from-user", default=None, help="Tweets from this user.")
@click.option("--to-user", default=None, help="Tweets to this user.")
@click.option("--hashtags", "adv_hashtags", default=None, help="Comma-separated hashtags.")
@click.option("--lang", default=None, help="Language filter.")
@click.option("--min-replies", default=None, type=int)
@click.option("--min-retweets", default=None, type=int)
@click.option("--min-likes", default=None, type=int)
@click.option("--is-reply/--no-is-reply", default=None)
@click.option("--has-media", is_flag=True, default=False)
@click.option("--since", default=None, help="Since date (YYYY-MM-DD).")
@click.option("--until", default=None, help="Until date (YYYY-MM-DD).")
def advanced(
    max_results: int | None,
    fmt: str | None,
    output_dir: str | None,
    preview: bool,
    keywords: str | None,
    from_user: str | None,
    to_user: str | None,
    adv_hashtags: str | None,
    lang: str | None,
    min_replies: int | None,
    min_retweets: int | None,
    min_likes: int | None,
    is_reply: bool | None,
    has_media: bool,
    since: str | None,
    until: str | None,
) -> None:
    """Advanced search with multiple filters."""
    console.print("[bold green]🔬 Running advanced search[/bold green]")

    kw_list = [k.strip() for k in keywords.split(",")] if keywords else None
    ht_list = [h.strip() for h in adv_hashtags.split(",")] if adv_hashtags else None

    scraper = XScraper()
    tweets = scraper.advanced_search(
        keywords=kw_list,
        from_user=from_user,
        to_user=to_user,
        hashtags=ht_list,
        lang=lang,
        min_replies=min_replies,
        min_retweets=min_retweets,
        min_likes=min_likes,
        is_reply=is_reply,
        has_media=has_media or None,
        since=since,
        until=until,
        max_results=max_results,
    )

    if not tweets:
        console.print("[red]No tweets found.[/red]")
        return

    if preview:
        preview_table(tweets, title="Advanced Search Results")

    resolved_fmt, resolved_dir = _resolve_output(fmt, output_dir)
    path = export_data(tweets, filename="advanced_search", fmt=resolved_fmt, output_dir=resolved_dir)
    console.print(f"\n[bold green]✅ Saved {len(tweets)} tweets → {path}[/bold green]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Fatal error: {}", e)
        console.print(f"\n[red]❌ Fatal error: {e}[/red]")
        sys.exit(1)
