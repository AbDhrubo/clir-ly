"""
Base crawler class for all news sites.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Generator, Set
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import Article
from .http_client import HttpClient
from .storage import ArticleStorage, CrawlProgress

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """
    Abstract base class for news site crawlers.
    
    All site-specific crawlers inherit from this and implement:
    - discover_article_urls(): Find article URLs from category pages
    - parse_article(): Extract content from article HTML
    """
    
    SOURCE_NAME: str = ""  # Unique identifier
    LANGUAGE: str = ""     # 'en' or 'bn'
    BASE_URL: str = ""     # Site base URL
    CATEGORIES: List[str] = []  # Category paths to crawl
    
    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        storage: Optional[ArticleStorage] = None,
        output_path: Optional[str] = None,
    ):
        self.client = http_client or HttpClient()
        self.storage = storage or ArticleStorage(output_path or f"data/raw/{self.SOURCE_NAME}_articles.jsonl")
        self.progress = CrawlProgress()
        self._seen_urls: Set[str] = set()
    
    @abstractmethod
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from a category page."""
        pass
    
    @abstractmethod
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content from HTML."""
        pass
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article."""
        if self.storage.is_duplicate(url):
            logger.debug(f"Skipping duplicate: {url}")
            return None
        
        html = self.client.get(url, language=self.LANGUAGE)
        if not html:
            return None
        
        article = self.parse_article(url, html)
        if article and self.storage.save(article):
            self.progress.add_crawled_url(self.SOURCE_NAME, url)
            return article
        
        return None
    
    def crawl(
        self,
        limit: int = 250,
        categories: Optional[List[str]] = None,
    ) -> int:
        """
        Crawl articles from this news source.
        
        Args:
            limit: Maximum number of articles to crawl
            categories: Categories to crawl (default: all)
        
        Returns:
            Number of articles crawled
        """
        categories = categories or self.CATEGORIES
        if not categories:
            logger.warning(f"No categories defined for {self.SOURCE_NAME}")
            return 0
        
        articles_per_category = max(1, limit // len(categories) + 1)
        total_crawled = 0
        
        for category in categories:
            if total_crawled >= limit:
                break
            
            logger.info(f"[{self.SOURCE_NAME}] Crawling category: {category}")
            category_count = 0
            
            for article_url in self.discover_article_urls(category):
                if category_count >= articles_per_category or total_crawled >= limit:
                    break
                
                article = self.crawl_article(article_url)
                if article:
                    total_crawled += 1
                    category_count += 1
                    # Truncate title for logging
                    title_preview = article.title[:40] if len(article.title) > 40 else article.title
                    logger.info(f"[{self.SOURCE_NAME}][{total_crawled}/{limit}] {title_preview}...")
        
        logger.info(f"[{self.SOURCE_NAME}] Finished. Total: {total_crawled} articles")
        return total_crawled
    
    # === Helper methods ===
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract article title."""
        # Try h1 first
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        
        # Fallback to og:title
        og_title = soup.find("meta", property="og:title")
        if og_title:
            return og_title.get("content", "").strip()
        
        return None
    
    def _extract_body(self, soup: BeautifulSoup, selectors: List[str] = None) -> str:
        """Extract article body text."""
        selectors = selectors or ["article", "div.article-content", "div.story-content"]
        
        body_parts = []
        
        # Try each selector
        for selector in selectors:
            if "." in selector:
                tag, class_pattern = selector.split(".", 1)
                container = soup.find(tag, class_=re.compile(class_pattern, re.I))
            else:
                container = soup.find(selector)
            
            if container:
                for p in container.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        body_parts.append(text)
                
                if body_parts:
                    break
        
        # Fallback: get all paragraphs
        if not body_parts:
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if text and len(text) > 50:
                    body_parts.append(text)
        
        return "\n\n".join(body_parts)
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date."""
        # Try time element
        time_elem = soup.find("time")
        if time_elem:
            return time_elem.get("datetime") or time_elem.get_text(strip=True)
        
        # Try meta tag
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            return date_meta.get("content")
        
        return None
    
    def _extract_category_from_url(self, url: str) -> str:
        """Extract category from URL path."""
        path = url.replace(self.BASE_URL, "").strip("/")
        parts = path.split("/")
        if parts:
            return parts[0]
        return "general"
    
    def _contains_bangla(self, text: str) -> bool:
        """Check if text contains Bangla characters."""
        return bool(re.search(r"[\u0980-\u09FF]", text))
    
    def _is_valid_article_url(self, url: str) -> bool:
        """Basic validation for article URLs."""
        skip_patterns = ["/video/", "/photo/", "/author/", "/topic/", "/tag/", 
                         "/category/", "/page/", "/search", "/login", "/register"]
        for pattern in skip_patterns:
            if pattern in url.lower():
                return False
        return True
