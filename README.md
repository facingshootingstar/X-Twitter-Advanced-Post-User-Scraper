<![CDATA[# 🐦 X (Twitter) Advanced Post & User Scraper

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Twitter API v2](https://img.shields.io/badge/Twitter%20API-v2-1DA1F2?logo=twitter&logoColor=white)](https://developer.twitter.com)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A **production-grade** X (Twitter) data extraction engine for researchers, marketers, and analysts. Scrape tweets, replies, user profiles, engagement metrics, hashtags, and follower networks using Twitter API v2 with intelligent Playwright browser fallback — all through a beautiful CLI interface.

> **Built for professionals who need reliable, structured Twitter data at scale.**

---

## 📑 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [Output Formats](#-output-formats)
- [Rate Limiting & Anti-Detection](#-rate-limiting--anti-detection)
- [Ethical Use Policy](#%EF%B8%8F-ethical-use-policy)
- [Service Pricing Guide](#-service-pricing-guide)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Keyword Search** | Search tweets by keyword, phrase, or complex boolean queries |
| 🔬 **Advanced Search** | Filter by user, hashtags, language, engagement thresholds, media, date ranges |
| 👤 **User Timeline** | Extract any public user's tweet history (with or without replies) |
| 📋 **Profile Extraction** | Full user profile data: bio, location, metrics, verification status |
| 👥 **Follower/Following** | Map social graphs — extract followers and following lists |
| 💬 **Reply Threads** | Fetch full reply threads for any tweet via conversation_id |
| #️⃣ **Hashtag Tracking** | Monitor hashtag trends with language filtering |
| 📊 **Engagement Metrics** | Likes, retweets, replies, quotes, bookmarks, impressions |
| 🌐 **Browser Fallback** | Playwright-powered headless scraping when API limits are reached |
| 📁 **Multi-Format Export** | CSV, JSON, and Excel output with automatic timestamping |

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────┐
│                     CLI (main.py)                     │
│              Click commands + Rich UI                 │
├──────────────────────────────────────────────────────┤
│                   XScraper Façade                     │
│            Unified API for all operations             │
├─────────────────────┬────────────────────────────────┤
│  TwitterAPIScraper  │       BrowserScraper           │
│    (tweepy v2)      │      (Playwright)              │
│    ── Primary ──    │    ── Fallback ──              │
├─────────────────────┴────────────────────────────────┤
│              Shared Utilities Layer                    │
│   Logging · Export · Dedup · Query Builder · Clean    │
├──────────────────────────────────────────────────────┤
│           Config (Pydantic + .env)                    │
└──────────────────────────────────────────────────────┘
```

---

## 🛠 Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Core runtime |
| tweepy | 4.15.0 | Twitter API v2 client |
| httpx | 0.28.1 | Async HTTP client |
| Playwright | 1.49.1 | Headless browser fallback |
| Pydantic | 2.10.5 | Config validation |
| pandas | 2.2.3 | Data manipulation & export |
| Rich | 13.9.4 | Terminal UI & tables |
| Click | 8.1.8 | CLI framework |
| Loguru | 0.7.3 | Structured logging |
| tenacity | 9.0.0 | Retry with backoff |
| orjson | 3.10.14 | Fast JSON serialisation |
| fake-useragent | 2.0.3 | User-agent rotation |
| openpyxl | 3.1.5 | Excel export |
| tqdm | 4.67.1 | Progress bars |

---

## 📁 Project Structure

```
X-Twitter-Advanced-Post-User-Scraper/
├── main.py                # CLI entry point — all commands
├── scraper.py             # Core scraping engine (API + Browser)
├── config.py              # Pydantic config loader
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── .gitignore             # Git exclusions
├── README.md              # This file
├── LICENSE                # MIT License
├── utils/
│   ├── __init__.py
│   └── helpers.py         # Logging, export, dedup, query builder
├── output/                # Scraped data (auto-created, git-ignored)
└── logs/                  # Log files (auto-created, git-ignored)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- Twitter API v2 Bearer Token ([Get one here](https://developer.twitter.com/en/portal/dashboard))

### Installation

```bash
# Clone the repository
git clone https://github.com/facingshootingstar/X-Twitter-Advanced-Post-User-Scraper.git
cd X-Twitter-Advanced-Post-User-Scraper

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (optional — for browser fallback)
playwright install chromium

# Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` and add your Twitter API credentials.

---

## 📖 Usage

### Search Tweets

```bash
# Basic keyword search
python main.py search "artificial intelligence"

# Search with limits and format
python main.py search "python programming" --max 200 --format json

# Sort by recency
python main.py search "breaking news" --sort recency --max 100
```

### User Timeline

```bash
# Fetch a user's tweets
python main.py user-tweets elonmusk --max 100

# Include replies
python main.py user-tweets openai --max 200 --replies
```

### User Profile

```bash
# Single profile
python main.py user-profile elonmusk

# Multiple profiles
python main.py user-profiles elonmusk openai Google --format excel
```

### Hashtag Search

```bash
# Search by hashtag
python main.py hashtag python --max 300

# With language filter
python main.py hashtag AI --lang en --max 500
```

### Followers & Following

```bash
# Get followers
python main.py followers elonmusk --max 500

# Get following
python main.py following openai --max 300
```

### Tweet Replies

```bash
# Fetch replies to a specific tweet
python main.py replies 1234567890123456789 --max 100
```

### Advanced Search

```bash
# Multi-filter search
python main.py advanced \
  --keywords "AI,machine learning" \
  --from-user openai \
  --lang en \
  --min-likes 100 \
  --has-media \
  --since 2024-01-01

# Search with engagement thresholds
python main.py advanced \
  --hashtags "python,coding" \
  --min-retweets 50 \
  --min-replies 10 \
  --format excel
```

### Global Options

```bash
# Enable debug logging
python main.py --debug search "test"

# Custom output directory
python main.py search "data" --output-dir ./my_data

# Disable preview table
python main.py search "quiet" --no-preview
```

---

## ⚙ Configuration

All settings are managed via `.env` file. See [`.env.example`](.env.example) for all options.

| Variable | Default | Description |
|----------|---------|-------------|
| `TWITTER_BEARER_TOKEN` | *required* | API v2 Bearer Token |
| `MAX_TWEETS` | `500` | Default max tweets per query |
| `MIN_DELAY` / `MAX_DELAY` | `1.5` / `4.0` | Rate-limit delay range (seconds) |
| `OUTPUT_FORMAT` | `csv` | Default export format |
| `OUTPUT_DIR` | `./output` | Output directory |
| `USE_BROWSER_FALLBACK` | `false` | Enable Playwright fallback |
| `HEADLESS` | `true` | Browser headless mode |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 📁 Output Formats

### CSV (Default)
```
output/search_AI_20240115_143022.csv
```

### JSON
```json
[
  {
    "id": "1234567890",
    "text": "Tweet content here…",
    "author_username": "user",
    "like_count": 42,
    "retweet_count": 10,
    "hashtags": ["AI", "python"],
    "scraped_at": "2024-01-15T14:30:22+00:00"
  }
]
```

### Excel
```
output/search_AI_20240115_143022.xlsx
```

Each record includes 20+ structured fields including full engagement metrics, extracted entities (hashtags, mentions, URLs), cleaned text, and metadata.

---

## 🛡 Rate Limiting & Anti-Detection

- **Automatic rate-limit handling** via tweepy's `wait_on_rate_limit`
- **Exponential backoff** with jitter on 429/5xx errors (up to 5 retries)
- **Configurable delays** between requests (`MIN_DELAY` / `MAX_DELAY`)
- **Browser stealth** with webdriver flag removal and realistic viewport
- **User-agent rotation** for browser scraping mode
- **Deduplication** engine to prevent redundant data

---

## ⚖️ Ethical Use Policy

> **This tool is designed for legitimate research, journalism, and business analytics.**

### ✅ Acceptable Use
- Academic research and sentiment analysis
- Brand monitoring and competitive intelligence
- Journalism and public interest investigations
- Marketing research with aggregated, anonymised data

### ❌ Prohibited Use
- Stalking, harassment, or surveillance of individuals
- Collecting data for discriminatory purposes
- Violating Twitter/X Terms of Service
- Reselling raw personal data
- Building profiles for unauthorized targeting

### Legal Compliance
- Always comply with Twitter's [Terms of Service](https://twitter.com/en/tos) and [Developer Agreement](https://developer.twitter.com/en/developer-terms/agreement)
- Respect GDPR, CCPA, and applicable data privacy laws
- Store data securely and implement data retention policies
- Obtain necessary consent where required by law
- This tool does **not** bypass authentication or access private data

> **The authors assume no liability for misuse. Users are solely responsible for ensuring their use complies with all applicable laws and platform policies.**

---

## 💰 Service Pricing Guide

This tool can be packaged as a professional fixed-price data extraction service.

### Pricing Tiers

| Tier | Price Range | Deliverables |
|------|-------------|--------------|
| **Basic** | $800 – $1,200 | Single-keyword or single-user scrape, CSV/JSON export, up to 10K tweets |
| **Professional** | $1,200 – $1,800 | Multi-keyword/user scraping, advanced filters, Excel reports with analytics, up to 50K tweets |
| **Enterprise** | $1,800 – $2,500 | Full deployment, custom queries, scheduled scraping, follower network mapping, API integration, ongoing support |

### Value Proposition for Clients

- **Time savings**: Manual data collection would take 40–100+ hours
- **Data quality**: Structured, deduplicated, analysis-ready output
- **Scale**: Thousands of data points collected in minutes
- **Compliance**: Ethical, API-based extraction (no TOS violations)
- **Expertise**: Professional-grade code with retry logic and error handling

### Where to Sell

- **Upwork / Fiverr** — Fixed-price gigs for "Twitter data extraction"
- **Toptal / Gun.io** — Premium freelance platforms
- **Direct outreach** — Marketing agencies, PR firms, research labs
- **Productized service** — Monthly subscription for ongoing monitoring

### Client Pitch Template

> *"I provide professional X/Twitter data extraction services for market research, brand monitoring, and competitive intelligence. Using enterprise-grade tooling with full API compliance, I deliver structured datasets (CSV/JSON/Excel) with engagement metrics, sentiment-ready text, and network mapping. Typical turnaround: 24–48 hours."*

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built with ❤️ for data professionals</strong><br>
  <sub>If this tool saves you time, consider giving it a ⭐</sub>
</p>
]]>
