"""
Main CLI for multi-source news crawler.

Supports crawling from 10 news sources:
- 5 English: Daily Star, New Age, Dhaka Tribune, Daily Sun, New Nation
- 5 Bangla: Prothom Alo, BD News 24, Kaler Kantho, Bangla Tribune, Dhaka Post

Usage:
    python -m src.crawler.main --source all --limit 2500
    python -m src.crawler.main --source english --limit 1250
    python -m src.crawler.main --source bangla --limit 1250
    python -m src.crawler.main --source daily_star --limit 250
    python -m src.crawler.main --source daily_sun --use-cloudscraper --limit 50
    python -m src.crawler.main --stats
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.crawler.http_client import HttpClient
from src.crawler.storage import ArticleStorage
from src.crawler.english_crawlers import ENGLISH_CRAWLERS
from src.crawler.bangla_crawlers import BANGLA_CRAWLERS
from src.crawler.config import RAW_DATA_DIR

# Try to import Selenium crawlers (may fail if selenium not installed)
try:
    from src.crawler.selenium_crawlers import SELENIUM_CRAWLERS
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_CRAWLERS = {}
    SELENIUM_AVAILABLE = False

# Try to import Cloudscraper crawlers (recommended for Cloudflare bypass)
try:
    from src.crawler.cloudscraper_crawlers import CLOUDSCRAPER_CRAWLERS
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_CRAWLERS = {}
    CLOUDSCRAPER_AVAILABLE = False

# Try to import Tavily crawlers (for heavily protected sites)
try:
    from src.crawler.tavily_crawlers import TAVILY_CRAWLERS
    from src.crawler.tavily_client import is_tavily_available
    TAVILY_AVAILABLE = is_tavily_available()
except ImportError:
    TAVILY_CRAWLERS = {}
    TAVILY_AVAILABLE = False

# All available crawlers (default: requests-based)
ALL_CRAWLERS = {**ENGLISH_CRAWLERS, **BANGLA_CRAWLERS}

# Sites that need special bypass (blocked by 403/Cloudflare)
BLOCKED_SITES = ["daily_sun", "bdnews24", "kaler_kantho"]

# Sites that need Tavily (aggressive Cloudflare)
TAVILY_SITES = ["bdnews24", "kaler_kantho"]

# Categorized sources
ENGLISH_SOURCES = list(ENGLISH_CRAWLERS.keys())
BANGLA_SOURCES = list(BANGLA_CRAWLERS.keys())

# Configure logging
def setup_logging(verbose: bool = False):
    """Configure logging for the crawler."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Console handler with UTF-8 support
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Use a simpler format to avoid encoding issues
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # File handler
    log_file = RAW_DATA_DIR / "crawler.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def crawl_source(source_name: str, limit: int = 250, http_client: HttpClient = None, 
                 use_selenium: bool = False, use_cloudscraper: bool = False,
                 use_tavily: bool = False) -> int:
    """
    Crawl a specific news source.
    
    Args:
        source_name: Name of the source (e.g., 'daily_star', 'prothom_alo')
        limit: Maximum articles to crawl
        http_client: Shared HTTP client instance
        use_selenium: Use Selenium for Cloudflare-protected sites
        use_cloudscraper: Use cloudscraper for Cloudflare bypass
        use_tavily: Use Tavily API for heavily protected sites (bdnews24, kaler_kantho)
    
    Returns:
        Number of articles crawled
    """
    # Determine which crawler to use (priority: tavily > cloudscraper > selenium > default)
    if use_tavily and source_name in TAVILY_SITES:
        if not TAVILY_AVAILABLE:
            logging.error("Tavily not available. Set TAVILY_API_KEY in .env file.")
            return 0
        crawler_class = TAVILY_CRAWLERS.get(source_name)
        if not crawler_class:
            logging.error(f"No Tavily crawler for: {source_name}")
            return 0
        logging.info(f"Using Tavily crawler for: {source_name}")
    elif use_cloudscraper and source_name in BLOCKED_SITES:
        if not CLOUDSCRAPER_AVAILABLE:
            logging.error("Cloudscraper not available. Install with: pip install cloudscraper")
            return 0
        crawler_class = CLOUDSCRAPER_CRAWLERS.get(source_name)
        if not crawler_class:
            logging.error(f"No cloudscraper crawler for: {source_name}")
            return 0
        logging.info(f"Using cloudscraper crawler for: {source_name}")
    elif use_selenium and source_name in BLOCKED_SITES:
        if not SELENIUM_AVAILABLE:
            logging.error("Selenium not available. Install with: pip install selenium webdriver-manager")
            return 0
        crawler_class = SELENIUM_CRAWLERS.get(source_name)
        if not crawler_class:
            logging.error(f"No Selenium crawler for: {source_name}")
            return 0
        logging.info(f"Using Selenium crawler for: {source_name}")
    elif source_name in ALL_CRAWLERS:
        crawler_class = ALL_CRAWLERS[source_name]
    else:
        logging.error(f"Unknown source: {source_name}")
        return 0
    
    output_path = RAW_DATA_DIR / f"{source_name}_articles.jsonl"
    
    http_client = http_client or HttpClient()
    storage = ArticleStorage(output_path)
    
    crawler = crawler_class(http_client=http_client, storage=storage)
    
    logging.info(f"Starting crawl: {source_name} (limit: {limit})")
    return crawler.crawl(limit=limit)


def crawl_multiple_sources(sources: list, total_limit: int = 2500, 
                           use_selenium: bool = False, use_cloudscraper: bool = False,
                           use_tavily: bool = False) -> dict:
    """
    Crawl multiple sources with evenly distributed limits.
    
    Args:
        sources: List of source names
        total_limit: Total articles across all sources
        use_selenium: Use Selenium for blocked sites
        use_cloudscraper: Use cloudscraper for blocked sites
        use_tavily: Use Tavily API for heavily protected sites
    
    Returns:
        Dict mapping source name to article count
    """
    per_source = total_limit // len(sources)
    http_client = HttpClient()  # Share client for rate limiting
    
    results = {}
    total = 0
    
    for source in sources:
        count = crawl_source(source, limit=per_source, http_client=http_client, 
                            use_selenium=use_selenium, use_cloudscraper=use_cloudscraper,
                            use_tavily=use_tavily)
        results[source] = count
        total += count
        print(f"  ✓ {source}: {count} articles")
    
    print(f"\nTotal: {total} articles")
    return results


def show_statistics():
    """Display crawl statistics for all sources."""
    print("\n" + "=" * 60)
    print("CRAWL STATISTICS")
    print("=" * 60)
    
    total_articles = 0
    
    # English sources
    print("\n=== ENGLISH SOURCES ===")
    for source in ENGLISH_SOURCES:
        file_path = RAW_DATA_DIR / f"{source}_articles.jsonl"
        if file_path.exists():
            storage = ArticleStorage(file_path)
            count = storage.count()
            total_articles += count
            print(f"  {source}: {count} articles")
            
            # Sample article
            for article in storage.iter_articles():
                title_preview = article.title[:50] if len(article.title) > 50 else article.title
                print(f"    Sample: {title_preview}...")
                print(f"    Tokens: {article.tokens or 'N/A'}")
                break
        else:
            print(f"  {source}: No data")
    
    # Bangla sources
    print("\n=== BANGLA SOURCES ===")
    for source in BANGLA_SOURCES:
        file_path = RAW_DATA_DIR / f"{source}_articles.jsonl"
        if file_path.exists():
            storage = ArticleStorage(file_path)
            count = storage.count()
            total_articles += count
            print(f"  {source}: {count} articles")
            
            # Sample article
            for article in storage.iter_articles():
                title_preview = article.title[:50] if len(article.title) > 50 else article.title
                print(f"    Sample: {title_preview}...")
                print(f"    Tokens: {article.tokens or 'N/A'}")
                break
        else:
            print(f"  {source}: No data")
    
    print(f"\n{'=' * 60}")
    print(f"TOTAL ARTICLES: {total_articles}")
    print(f"{'=' * 60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Multi-source news crawler for CLIR dataset construction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Crawl all 10 sources (250 articles each = 2,500 total)
  python -m src.crawler.main --source all --limit 2500
  
  # Crawl only English sources
  python -m src.crawler.main --source english --limit 1250
  
  # Crawl only Bangla sources
  python -m src.crawler.main --source bangla --limit 1250
  
  # Crawl a specific source
  python -m src.crawler.main --source daily_star --limit 250
  
  # Show statistics
  python -m src.crawler.main --stats

Available sources:
  English: daily_star, newage, dhaka_tribune, daily_sun, new_nation
  Bangla: prothom_alo, bdnews24, kaler_kantho, bangla_tribune, dhaka_post
        """
    )
    
    parser.add_argument(
        "--source",
        choices=["all", "english", "bangla"] + list(ALL_CRAWLERS.keys()),
        default="all",
        help="Source(s) to crawl"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=2500,
        help="Maximum articles to crawl (default: 2500)"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show crawl statistics"
    )
    
    parser.add_argument(
        "--use-selenium",
        action="store_true",
        help="Use Selenium browser for Cloudflare-protected sites"
    )
    
    parser.add_argument(
        "--use-cloudscraper",
        action="store_true",
        help="Use cloudscraper for Cloudflare bypass (daily_sun)"
    )
    
    parser.add_argument(
        "--use-tavily",
        action="store_true",
        help="Use Tavily API for heavily protected sites (bdnews24, kaler_kantho). Requires TAVILY_API_KEY in .env"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Show stats and exit
    if args.stats:
        show_statistics()
        return
    
    # Determine sources to crawl
    print("\n" + "=" * 60)
    print("CLIR NEWS CRAWLER")
    print("=" * 60 + "\n")
    
    if args.source == "all":
        sources = ENGLISH_SOURCES + BANGLA_SOURCES
        print(f"Crawling ALL {len(sources)} sources (limit: {args.limit})\n")
    elif args.source == "english":
        sources = ENGLISH_SOURCES
        print(f"Crawling {len(sources)} ENGLISH sources (limit: {args.limit})\n")
    elif args.source == "bangla":
        sources = BANGLA_SOURCES
        print(f"Crawling {len(sources)} BANGLA sources (limit: {args.limit})\n")
    else:
        sources = [args.source]
        print(f"Crawling {args.source} (limit: {args.limit})\n")
    
    if args.use_tavily:
        print("Using Tavily API for bdnews24, kaler_kantho\n")
    elif args.use_cloudscraper:
        print("Using cloudscraper for Cloudflare bypass\n")
    elif args.use_selenium:
        print("Using Selenium for Cloudflare-protected sites\n")
    
    try:
        results = crawl_multiple_sources(sources, args.limit, 
                                         use_selenium=args.use_selenium,
                                         use_cloudscraper=args.use_cloudscraper,
                                         use_tavily=args.use_tavily)
        
        # Show summary
        print("\n" + "=" * 60)
        print("CRAWL COMPLETE")
        print("=" * 60)
        for source, count in results.items():
            print(f"  {source}: {count} articles")
        print(f"\nTotal: {sum(results.values())} articles")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nCrawl interrupted by user. Progress saved.")
        show_statistics()


if __name__ == "__main__":
    main()
