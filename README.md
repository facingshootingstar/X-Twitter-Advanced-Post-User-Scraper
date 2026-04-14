<div align="center">

# 🐦 X (Twitter) Advanced Post & User Scraper

**A high-performance Python scraping engine for extracting tweets, replies, user profiles, engagement metrics, and hashtag data from X (formerly Twitter) — powered by Playwright stealth automation.**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-1.52-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Features](#-key-features) · [Quick Start](#-quick-start) · [Usage](#-usage) · [Export](#-export-formats)

</div>

---

## 📌 About This Project

A personal automation project exploring advanced web scraping techniques on the X (Twitter) platform. This tool demonstrates expertise in browser automation, anti-detection strategies, async Python patterns, and structured data extraction — built as a learning exercise and portfolio piece.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Tweet Extraction** | Full tweet text, media URLs, timestamps, engagement counts (likes, retweets, replies, views) |
| 👤 **User Profile Scraping** | Bio, follower/following counts, join date, verification status, profile images |
| 💬 **Reply & Thread Parsing** | Nested reply chains with parent-child relationships |
| #️⃣ **Hashtag & Keyword Search** | Search by keyword, hashtag, or advanced query operators |
| 🛡️ **Full Stealth Mode** | Anti-bot-detection with fingerprint spoofing, navigator overrides, and randomized behavior |
| 🧠 **Human-Like Behavior** | Random typing delays, scroll patterns, and page-interaction timing |
| 📦 **Multi-Format Export** | CSV, XLSX (auto-width columns), and JSON output with timestamps |
| 🔄 **Batch Scraping** | Process multiple queries or user profiles from a configuration file |
| 🔁 **Auto-Retry with Backoff** | Tenacity-powered exponential backoff on transient failures |
| 📊 **Rich CLI Dashboard** | Beautiful terminal output with progress bars, tables, and colored logs |

---

## 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Core runtime |
| Playwright | Browser automation engine |
| Rich | Terminal UI, logging, tables |
| Pandas | Data manipulation & export |
| openpyxl | Excel (.xlsx) writer |
| Tenacity | Retry logic with backoff |
| fake-useragent | Randomized user-agent strings |
| python-dotenv | Environment configuration |
| aiofiles | Async file I/O |

---

## 📁 Project Structure

```
X-Twitter-Advanced-Post-User-Scraper/
├── main.py                 # CLI entry-point with argparse
├── scraper.py              # Core Playwright scraping engine
├── config.py               # Centralized configuration loader
├── requirements.txt        # Pinned dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git exclusions
├── LICENSE                 # MIT License
├── README.md               # This file
└── utils/
    ├── __init__.py
    └── helpers.py          # Logging, stealth, export, dedup utilities
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** installed ([download](https://www.python.org/downloads/))
- **Git** installed
- A valid **X (Twitter) Developer API key** ([get one here](https://developer.twitter.com/en/portal/dashboard))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/facingshootingstar/X-Twitter-Advanced-Post-User-Scraper.git
cd X-Twitter-Advanced-Post-User-Scraper

# 2. Create & activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env with your credentials and preferences
```

---

## 📖 Usage

### Search Tweets by Keyword
```bash
python main.py search -q "machine learning" -n 100
```

### Scrape User Profile
```bash
python main.py profile -u "elonmusk" --include-tweets
```

### Hashtag Extraction
```bash
python main.py search -q "#python" -n 50 -f xlsx
```

### Batch Mode
```bash
python main.py --batch queries.txt -n 30 -f csv
```

### Debug Mode (Visible Browser)
```bash
python main.py search -q "AI news" --no-headless
```

---

## 📤 Export Formats

All exports are saved to the `output/` directory with timestamps.

### CSV
```csv
tweet_id,author,text,likes,retweets,replies,views,timestamp,url
17283...,@user,"Example tweet...",142,23,5,12847,2026-04-15T10:30:00Z,https://...
```

### JSON
```json
[
  {
    "tweet_id": "1728300000000000000",
    "author": "@user",
    "text": "Example tweet...",
    "likes": 142,
    "retweets": 23,
    "replies": 5,
    "views": 12847,
    "timestamp": "2026-04-15T10:30:00Z",
    "url": "https://x.com/user/status/..."
  }
]
```

### XLSX
- Auto-sized columns
- Ready for analysis in Excel or Google Sheets

---

## ⚖️ Ethical Usage & Legal Disclaimer

> **⚠️ This tool is for educational and research purposes only.**

- **Respect X's Terms of Service.** Automated scraping may violate platform ToS. Use at your own risk.
- **Comply with local laws**, including GDPR, CCPA, and other data privacy regulations.
- **Do not use** extracted data for spamming, harassment, or any unlawful activity.
- **Rate-limit your requests** to avoid overloading servers. The built-in delays are designed for responsible use.
- The author assumes **no liability** for misuse of this software.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [@facingshootingstar](https://github.com/facingshootingstar)**

*Made for personal learning and portfolio purposes.*

</div>
