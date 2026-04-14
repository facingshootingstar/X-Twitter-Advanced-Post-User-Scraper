"""
config.py — Centralised configuration for X (Twitter) Advanced Scraper.

Loads settings from .env and exposes validated Pydantic models so every
module can simply `from config import settings`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH)


# ---------------------------------------------------------------------------
# Twitter API credentials
# ---------------------------------------------------------------------------
class TwitterAPIConfig(BaseModel):
    """Twitter API v2 credentials (Bearer + OAuth 1.0a)."""

    bearer_token: str = Field(
        default_factory=lambda: os.getenv("TWITTER_BEARER_TOKEN", ""),
    )
    api_key: str = Field(
        default_factory=lambda: os.getenv("TWITTER_API_KEY", ""),
    )
    api_secret: str = Field(
        default_factory=lambda: os.getenv("TWITTER_API_SECRET", ""),
    )
    access_token: str = Field(
        default_factory=lambda: os.getenv("TWITTER_ACCESS_TOKEN", ""),
    )
    access_secret: str = Field(
        default_factory=lambda: os.getenv("TWITTER_ACCESS_SECRET", ""),
    )

    @field_validator("bearer_token")
    @classmethod
    def _bearer_not_placeholder(cls, v: str) -> str:
        if v in ("", "your_bearer_token_here"):
            raise ValueError(
                "TWITTER_BEARER_TOKEN is missing or still the placeholder. "
                "Set it in your .env file."
            )
        return v


# ---------------------------------------------------------------------------
# Scraper behaviour
# ---------------------------------------------------------------------------
class ScraperConfig(BaseModel):
    """Runtime tunables for the scraping engine."""

    max_tweets: int = Field(
        default_factory=lambda: int(os.getenv("MAX_TWEETS", "500")),
        ge=1,
        le=100_000,
    )
    min_delay: float = Field(
        default_factory=lambda: float(os.getenv("MIN_DELAY", "1.5")),
        ge=0.0,
    )
    max_delay: float = Field(
        default_factory=lambda: float(os.getenv("MAX_DELAY", "4.0")),
        ge=0.0,
    )
    output_format: str = Field(
        default_factory=lambda: os.getenv("OUTPUT_FORMAT", "csv").lower(),
    )
    output_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./output")),
    )
    use_browser_fallback: bool = Field(
        default_factory=lambda: os.getenv("USE_BROWSER_FALLBACK", "false").lower()
        == "true",
    )
    headless: bool = Field(
        default_factory=lambda: os.getenv("HEADLESS", "true").lower() == "true",
    )

    @field_validator("output_format")
    @classmethod
    def _valid_format(cls, v: str) -> str:
        allowed = {"csv", "json", "excel"}
        if v not in allowed:
            raise ValueError(f"OUTPUT_FORMAT must be one of {allowed}, got '{v}'")
        return v


# ---------------------------------------------------------------------------
# Proxy
# ---------------------------------------------------------------------------
class ProxyConfig(BaseModel):
    """Optional proxy settings."""

    http_proxy: Optional[str] = Field(
        default_factory=lambda: os.getenv("HTTP_PROXY"),
    )
    https_proxy: Optional[str] = Field(
        default_factory=lambda: os.getenv("HTTPS_PROXY"),
    )

    @property
    def as_dict(self) -> dict[str, str]:
        proxies: dict[str, str] = {}
        if self.http_proxy:
            proxies["http://"] = self.http_proxy
        if self.https_proxy:
            proxies["https://"] = self.https_proxy
        return proxies


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
class LogConfig(BaseModel):
    """Logging configuration."""

    log_level: str = Field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper(),
    )
    log_file: Path = Field(
        default_factory=lambda: Path(os.getenv("LOG_FILE", "./logs/scraper.log")),
    )


# ---------------------------------------------------------------------------
# Aggregate settings
# ---------------------------------------------------------------------------
class Settings(BaseModel):
    """Top-level settings object that composes all sub-configs."""

    api: TwitterAPIConfig = Field(default_factory=TwitterAPIConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    log: LogConfig = Field(default_factory=LogConfig)


def load_settings() -> Settings:
    """Instantiate and return validated settings."""
    return Settings()


# Singleton — import this everywhere
settings: Settings | None = None


def get_settings() -> Settings:
    """Lazy-load settings so import-time errors don't fire during tests."""
    global settings
    if settings is None:
        settings = load_settings()
    return settings
