"""
utils/helpers.py — Shared utility functions for the X (Twitter) Scraper.

Contains: logging setup, rate-limit helpers, data export, text cleaning,
timestamp handling, and retry decorators.
"""

from __future__ import annotations

import asyncio
import hashlib
import random
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import orjson
import pandas as pd
from loguru import logger
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------------------------
# Rich console (shared across project)
# ---------------------------------------------------------------------------
console = Console()


# ---------------------------------------------------------------------------
# Logging bootstrap
# ---------------------------------------------------------------------------
def setup_logging(log_level: str = "INFO", log_file: Path | str = "./logs/scraper.log") -> None:
    """Configure loguru sinks (stderr + rotating file)."""
    logger.remove()  # Remove default sink
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
    )
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(log_path),
        level=log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} — {message}",
    )
    logger.info("Logging initialised → level={}, file={}", log_level, log_path)


# ---------------------------------------------------------------------------
# Rate-limit / delay helpers
# ---------------------------------------------------------------------------
async def smart_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Async sleep with jittered delay to avoid detection."""
    delay = random.uniform(min_s, max_s)
    logger.debug("Sleeping {:.2f}s …", delay)
    await asyncio.sleep(delay)


def sync_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Synchronous jittered delay (for non-async call paths)."""
    import time

    delay = random.uniform(min_s, max_s)
    logger.debug("Sleeping {:.2f}s …", delay)
    time.sleep(delay)


# ---------------------------------------------------------------------------
# Text cleaning
# ---------------------------------------------------------------------------
_URL_RE = re.compile(r"https?://\S+")
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_RE = re.compile(r"#\w+")
_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str, *, strip_urls: bool = False, strip_mentions: bool = False) -> str:
    """Normalise tweet text for downstream analysis."""
    text = unicodedata.normalize("NFKC", text)
    if strip_urls:
        text = _URL_RE.sub("", text)
    if strip_mentions:
        text = _MENTION_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def extract_hashtags(text: str) -> list[str]:
    """Return lowercase hashtags found in *text*."""
    return [tag.lower() for tag in _HASHTAG_RE.findall(text)]


def extract_mentions(text: str) -> list[str]:
    """Return @mentions found in *text* (without the @)."""
    return [m.lstrip("@") for m in _MENTION_RE.findall(text)]


def extract_urls(text: str) -> list[str]:
    """Return URLs found in *text*."""
    return _URL_RE.findall(text)


# ---------------------------------------------------------------------------
# Timestamp helpers
# ---------------------------------------------------------------------------
def iso_now() -> str:
    """UTC ISO-8601 timestamp string."""
    return datetime.now(timezone.utc).isoformat()


def parse_twitter_date(date_str: str) -> datetime:
    """Parse Twitter's date format → timezone-aware datetime."""
    # Twitter API v2 returns ISO-8601
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        # Fallback for v1.1 style: "Mon Jan 01 00:00:00 +0000 2024"
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")


# ---------------------------------------------------------------------------
# Data export
# ---------------------------------------------------------------------------
def export_data(
    records: Sequence[dict[str, Any]],
    *,
    output_dir: Path | str = "./output",
    filename: str = "tweets",
    fmt: str = "csv",
) -> Path:
    """
    Export a list of dicts to the chosen format.

    Returns the path of the written file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{filename}_{timestamp}"

    if fmt == "csv":
        path = output_dir / f"{base}.csv"
        df = pd.DataFrame(records)
        df.to_csv(path, index=False, encoding="utf-8-sig")

    elif fmt == "excel":
        path = output_dir / f"{base}.xlsx"
        df = pd.DataFrame(records)
        df.to_excel(path, index=False, engine="openpyxl")

    elif fmt == "json":
        path = output_dir / f"{base}.json"
        with open(path, "wb") as fh:
            fh.write(orjson.dumps(records, option=orjson.OPT_INDENT_2))

    else:
        raise ValueError(f"Unsupported format: {fmt}")

    logger.success("Exported {} records → {}", len(records), path)
    return path


# ---------------------------------------------------------------------------
# De-duplication
# ---------------------------------------------------------------------------
def dedup_by_key(records: list[dict], key: str = "id") -> list[dict]:
    """Remove duplicate records based on a dict key."""
    seen: set[str] = set()
    unique: list[dict] = []
    for rec in records:
        val = str(rec.get(key, ""))
        if val not in seen:
            seen.add(val)
            unique.append(rec)
    removed = len(records) - len(unique)
    if removed:
        logger.info("De-duplicated: removed {} duplicates (key='{}')", removed, key)
    return unique


def record_hash(record: dict) -> str:
    """SHA-256 fingerprint of a record for dedup / caching."""
    raw = orjson.dumps(record, option=orjson.OPT_SORT_KEYS)
    return hashlib.sha256(raw).hexdigest()


# ---------------------------------------------------------------------------
# Rich table preview
# ---------------------------------------------------------------------------
def preview_table(records: Sequence[dict[str, Any]], *, max_rows: int = 15, title: str = "Preview") -> None:
    """Print a pretty Rich table to the terminal."""
    if not records:
        console.print("[yellow]No records to preview.[/yellow]")
        return

    table = Table(title=title, show_lines=True, header_style="bold magenta")
    columns = list(records[0].keys())
    for col in columns:
        table.add_column(col, overflow="fold", max_width=50)

    for rec in records[:max_rows]:
        table.add_row(*[str(rec.get(c, "")) for c in columns])

    if len(records) > max_rows:
        table.add_row(*["…" for _ in columns])

    console.print(table)


# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------
def chunk_list(lst: list, size: int) -> list[list]:
    """Split *lst* into chunks of *size*."""
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def build_query(
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
) -> str:
    """
    Build a Twitter API v2-compatible search query string.

    Example output:
        '(python OR scraping) from:elonmusk lang:en -is:retweet has:media'
    """
    parts: list[str] = []

    if keywords:
        kw = " OR ".join(keywords)
        parts.append(f"({kw})" if len(keywords) > 1 else kw)

    if from_user:
        parts.append(f"from:{from_user}")
    if to_user:
        parts.append(f"to:{to_user}")

    if hashtags:
        for tag in hashtags:
            tag = tag.lstrip("#")
            parts.append(f"#{tag}")

    if lang:
        parts.append(f"lang:{lang}")

    if min_replies is not None:
        parts.append(f"min_replies:{min_replies}")
    if min_retweets is not None:
        parts.append(f"min_retweets:{min_retweets}")
    if min_likes is not None:
        parts.append(f"min_faves:{min_likes}")

    if is_reply is True:
        parts.append("is:reply")
    elif is_reply is False:
        parts.append("-is:reply")

    if has_media:
        parts.append("has:media")

    # Note: since/until are passed as API params, not in query, but
    # we keep them here for builder completeness (web scraping path).
    if since:
        parts.append(f"since:{since}")
    if until:
        parts.append(f"until:{until}")

    query = " ".join(parts)
    logger.debug("Built query → {}", query)
    return query
