"""
News crawler package for CLIR dataset construction.

Supports 10 news sources:
- 5 English: Daily Star, New Age, Dhaka Tribune, Daily Sun, New Nation
- 5 Bangla: Prothom Alo, BD News 24, Kaler Kantho, Bangla Tribune, Dhaka Post
"""

from .models import Article
from .storage import ArticleStorage
from .http_client import HttpClient
from .base_crawler import BaseCrawler
from .english_crawlers import (
    DailyStarCrawler,
    NewAgeCrawler,
    DhakaTribuneCrawler,
    DailySunCrawler,
    NewNationCrawler,
    ENGLISH_CRAWLERS,
)
from .bangla_crawlers import (
    ProthomAloCrawler,
    BDNews24Crawler,
    KalerKanthoCrawler,
    BanglaTribuneCrawler,
    DhakaPostCrawler,
    BANGLA_CRAWLERS,
)

__all__ = [
    # Core
    "Article",
    "ArticleStorage",
    "HttpClient",
    "BaseCrawler",
    
    # English crawlers
    "DailyStarCrawler",
    "NewAgeCrawler",
    "DhakaTribuneCrawler",
    "DailySunCrawler",
    "NewNationCrawler",
    "ENGLISH_CRAWLERS",
    
    # Bangla crawlers
    "ProthomAloCrawler",
    "BDNews24Crawler",
    "KalerKanthoCrawler",
    "BanglaTribuneCrawler",
    "DhakaPostCrawler",
    "BANGLA_CRAWLERS",
]
