"""
Configuration settings for the news crawler.
"""

from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INDEX_DIR = DATA_DIR / "index"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# HTTP Client settings
REQUEST_TIMEOUT = 30  # seconds
REQUEST_DELAY = 2.0   # seconds between requests (be respectful)
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0   # exponential backoff multiplier

# User agents (rotate to avoid detection)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# === The Daily Star (English) ===
DAILY_STAR_BASE_URL = "https://www.thedailystar.net"
DAILY_STAR_CATEGORIES = [
    "/news/bangladesh",
    "/news/world",
    "/business",
    "/sports",
    "/opinion",
    "/environment",
    "/tech-startup",
]

# === Prothom Alo (Bangla) ===
PROTHOM_ALO_BASE_URL = "https://www.prothomalo.com"
PROTHOM_ALO_CATEGORIES = [
    "/bangladesh",
    "/world",
    "/politics",
    "/business",
    "/sports",
    "/entertainment",
    "/opinion",
]

# Crawl limits
DEFAULT_ARTICLES_PER_SOURCE = 2500
MAX_ARTICLES_PER_CATEGORY = 500  # Spread across categories

# Storage files
DAILY_STAR_OUTPUT = RAW_DATA_DIR / "daily_star_articles.jsonl"
PROTHOM_ALO_OUTPUT = RAW_DATA_DIR / "prothom_alo_articles.jsonl"
CRAWL_PROGRESS_FILE = RAW_DATA_DIR / "crawl_progress.json"
