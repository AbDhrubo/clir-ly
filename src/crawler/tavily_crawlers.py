"""
Tavily-based crawlers for heavily protected sites.

Uses Tavily API to extract content from sites with aggressive Cloudflare
protection that can't be bypassed with cloudscraper.

Sites covered:
- BD News 24 (bangla.bdnews24.com) - Bangla
- Kaler Kantho (kalerkantho.com) - Bangla
"""

import re
import logging
import atexit
from typing import Optional, Generator, List
from datetime import datetime

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_crawler import BaseCrawler
from .models import Article
from .tavily_client import get_tavily_client, is_tavily_available
from .cloudscraper_client import get_cloudscraper_client

logger = logging.getLogger(__name__)


class TavilyCrawlerMixin:
    """Mixin to add Tavily support to crawlers."""
    
    def _extract_with_tavily(self, url: str) -> Optional[dict]:
        """Extract content using Tavily API."""
        client = get_tavily_client()
        return client.extract(url)
    
    def _get_html_cloudscraper(self, url: str, language: str = "bn") -> Optional[str]:
        """Fetch HTML using cloudscraper for URL discovery."""
        client = get_cloudscraper_client()
        return client.get(url, language=language)


class BDNews24TavilyCrawler(BaseCrawler, TavilyCrawlerMixin):
    """
    Tavily-based crawler for BD News 24 Bangla.
    Uses Tavily API for content extraction to bypass aggressive protection.
    """
    
    SOURCE_NAME = "bdnews24"
    LANGUAGE = "bn"
    BASE_URL = "https://bangla.bdnews24.com"
    CATEGORIES = [
        "/bangladesh",
        "/politics",
        "/economy",
        "/world",
        "/sports",
        "/entertainment",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 2,
    ) -> Generator[str, None, None]:
        """
        Discover article URLs using cloudscraper for listing pages.
        Individual articles will be fetched via Tavily.
        """
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.info(f"[{self.SOURCE_NAME}] Discovering from: {url}")
            html = self._get_html_cloudscraper(url, self.LANGUAGE)
            
            if not html:
                # Try Tavily for listing page as fallback
                result = self._extract_with_tavily(url)
                if result and result.get("content"):
                    # Parse links from extracted content
                    # This is less reliable, so we continue to next category
                    pass
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{12-char-hex-id}
                if re.search(r"/[a-z0-9-]+/[a-f0-9]{12}$", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            logger.info(f"[{self.SOURCE_NAME}] Found {found} article URLs from {category}")
            if found == 0:
                break
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article using Tavily API."""
        if self.storage.is_duplicate(url):
            return None
        
        if not is_tavily_available():
            logger.error("Tavily API not available. Set TAVILY_API_KEY in .env file.")
            return None
        
        logger.info(f"[{self.SOURCE_NAME}] Tavily extracting: {url}")
        result = self._extract_with_tavily(url)
        
        if not result or not result.get("content"):
            logger.warning(f"[{self.SOURCE_NAME}] Tavily extraction failed: {url}")
            return None
        
        article = self._parse_tavily_result(url, result)
        if article and self.storage.save(article):
            self.progress.add_crawled_url(self.SOURCE_NAME, url)
            return article
        
        return None
    
    def _parse_tavily_result(self, url: str, result: dict) -> Optional[Article]:
        """Parse Tavily extraction result into Article."""
        try:
            title = result.get("title", "").strip()
            content = result.get("content", "").strip()
            
            if not title or not content:
                return None
            
            # Filter to keep only Bangla content
            body_parts = []
            for para in content.split("\n"):
                para = para.strip()
                if para and len(para) > 20 and self._contains_bangla(para):
                    body_parts.append(para)
            
            body = "\n\n".join(body_parts)
            if len(body) < 50:
                return None
            
            category = self._extract_category_from_url(url)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=datetime.now().isoformat(),
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
            )
        except Exception as e:
            logger.error(f"Error parsing Tavily result for {url}: {e}")
            return None
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Required by BaseCrawler - not used for Tavily crawlers."""
        # Tavily crawlers use _parse_tavily_result instead
        return None


class KalerKanthoTavilyCrawler(BaseCrawler, TavilyCrawlerMixin):
    """
    Tavily-based crawler for Kaler Kantho (Bangla).
    Uses Tavily API for content extraction to bypass aggressive protection.
    """
    
    SOURCE_NAME = "kaler_kantho"
    LANGUAGE = "bn"
    BASE_URL = "https://www.kalerkantho.com"
    CATEGORIES = [
        "/online/national",
        "/online/politics",
        "/online/world",
        "/online/business",
        "/online/sports",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 2,
    ) -> Generator[str, None, None]:
        """
        Discover article URLs.
        Note: Kaler Kantho may block even listing pages.
        """
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.info(f"[{self.SOURCE_NAME}] Discovering from: {url}")
            html = self._get_html_cloudscraper(url, self.LANGUAGE)
            
            if not html:
                logger.warning(f"[{self.SOURCE_NAME}] Could not fetch listing: {url}")
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /online/{category}/{year}/{month}/{day}/{article_id}
                if re.search(r"/online/[a-z-]+/\d{4}/\d{2}/\d{2}/\d+", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls:
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            logger.info(f"[{self.SOURCE_NAME}] Found {found} article URLs from {category}")
            if found == 0:
                break
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article using Tavily API."""
        if self.storage.is_duplicate(url):
            return None
        
        if not is_tavily_available():
            logger.error("Tavily API not available. Set TAVILY_API_KEY in .env file.")
            return None
        
        logger.info(f"[{self.SOURCE_NAME}] Tavily extracting: {url}")
        result = self._extract_with_tavily(url)
        
        if not result or not result.get("content"):
            logger.warning(f"[{self.SOURCE_NAME}] Tavily extraction failed: {url}")
            return None
        
        article = self._parse_tavily_result(url, result)
        if article and self.storage.save(article):
            self.progress.add_crawled_url(self.SOURCE_NAME, url)
            return article
        
        return None
    
    def _parse_tavily_result(self, url: str, result: dict) -> Optional[Article]:
        """Parse Tavily extraction result into Article."""
        try:
            title = result.get("title", "").strip()
            content = result.get("content", "").strip()
            
            if not title or not content:
                return None
            
            # Filter content
            body_parts = []
            for para in content.split("\n"):
                para = para.strip()
                if para and len(para) > 20:
                    body_parts.append(para)
            
            body = "\n\n".join(body_parts)
            if len(body) < 50:
                return None
            
            # Extract date from URL: /online/national/2026/01/19/1635439
            date_match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
            if date_match:
                date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            else:
                date_str = datetime.now().isoformat()
            
            category = self._extract_category_from_url(url)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=date_str,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
            )
        except Exception as e:
            logger.error(f"Error parsing Tavily result for {url}: {e}")
            return None
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Required by BaseCrawler - not used for Tavily crawlers."""
        # Tavily crawlers use _parse_tavily_result instead
        return None


# Registry of Tavily-based crawlers
TAVILY_CRAWLERS = {
    "bdnews24": BDNews24TavilyCrawler,
    "kaler_kantho": KalerKanthoTavilyCrawler,
}
