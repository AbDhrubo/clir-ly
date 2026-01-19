"""
Cloudscraper-based crawlers for Cloudflare-protected sites.

Uses cloudscraper which automatically solves Cloudflare challenges.

Sites covered:
- Daily Sun (daily-sun.com) - English
- BD News 24 (bangla.bdnews24.com) - Bangla  
- Kaler Kantho (kalerkantho.com) - Bangla
"""

import re
import logging
import atexit
from typing import Optional, Generator

from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base_crawler import BaseCrawler
from .models import Article
from .cloudscraper_client import get_cloudscraper_client, close_cloudscraper_client

logger = logging.getLogger(__name__)

# Register cleanup on exit
atexit.register(close_cloudscraper_client)


class CloudscraperCrawlerMixin:
    """Mixin to add cloudscraper support to crawlers."""
    
    def _get_html_cloudscraper(self, url: str, language: str = "en") -> Optional[str]:
        """Fetch HTML using cloudscraper with Cloudflare bypass."""
        client = get_cloudscraper_client()
        return client.get(url, language=language)


class DailySunCloudCrawler(BaseCrawler, CloudscraperCrawlerMixin):
    """
    Cloudscraper-based crawler for Daily Sun (English).
    Automatically bypasses Cloudflare protection.
    """
    
    SOURCE_NAME = "daily_sun"
    LANGUAGE = "en"
    BASE_URL = "https://www.daily-sun.com"
    CATEGORIES = [
        "/bangladesh",
        "/politics", 
        "/business",
        "/sports",
        "/world",
        "/opinion",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 3,
    ) -> Generator[str, None, None]:
        """Discover article URLs using cloudscraper."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.info(f"[{self.SOURCE_NAME}] Fetching: {url}")
            html = self._get_html_cloudscraper(url, self.LANGUAGE)
            
            if not html:
                logger.warning(f"[{self.SOURCE_NAME}] Failed to fetch: {url}")
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{numeric_id}/{slug}
                # Examples: /bangladesh/852534/all-but-2-dual-citizenship-candidates-cleared
                if re.search(r"/(bangladesh|politics|business|sports|world|opinion|entertainment|feature|sun-campus)/\d+/[a-z0-9-]+", href, re.I):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            logger.info(f"[{self.SOURCE_NAME}] Found {found} article URLs from {category}")
            if found == 0:
                break
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article using cloudscraper."""
        if self.storage.is_duplicate(url):
            return None
        
        html = self._get_html_cloudscraper(url, self.LANGUAGE)
        if not html:
            return None
        
        article = self.parse_article(url, html)
        if article and self.storage.save(article):
            self.progress.add_crawled_url(self.SOURCE_NAME, url)
            return article
        
        return None
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body = self._extract_body(soup, [
                "div.news-detail-content",
                "div.single-news-content",
                "div.news-details",
                "article",
            ])
            
            if len(body) < 100:
                return None
            
            date = self._extract_date(soup)
            category = self._extract_category_from_url(url)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=date,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
            )
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None


class BDNews24CloudCrawler(BaseCrawler, CloudscraperCrawlerMixin):
    """
    Cloudscraper-based crawler for BD News 24 Bangla.
    Automatically bypasses 403 blocks.
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
        max_pages: int = 3,
    ) -> Generator[str, None, None]:
        """Discover article URLs using cloudscraper."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.info(f"[{self.SOURCE_NAME}] Fetching: {url}")
            html = self._get_html_cloudscraper(url, self.LANGUAGE)
            
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{12-char-hex-id}
                # Examples: /bangladesh/79d5eb0c616f, /politics/eb7e47d98856
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
        """Crawl a single article using cloudscraper."""
        if self.storage.is_duplicate(url):
            return None
        
        html = self._get_html_cloudscraper(url, self.LANGUAGE)
        if not html:
            return None
        
        article = self.parse_article(url, html)
        if article and self.storage.save(article):
            self.progress.add_crawled_url(self.SOURCE_NAME, url)
            return article
        
        return None
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body_parts = []
            article_body = soup.find("article") or soup.find("div", class_=re.compile(r"story|article|content", re.I))
            
            if article_body:
                for p in article_body.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20 and self._contains_bangla(text):
                        body_parts.append(text)
            
            body = "\n\n".join(body_parts)
            if len(body) < 50:
                return None
            
            date = self._extract_date(soup)
            category = self._extract_category_from_url(url)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=date,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
            )
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None


class KalerKanthoCloudCrawler(BaseCrawler, CloudscraperCrawlerMixin):
    """
    Cloudscraper-based crawler for Kaler Kantho (Bangla).
    Automatically bypasses 403 blocks.
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
        max_pages: int = 3,
    ) -> Generator[str, None, None]:
        """Discover article URLs using cloudscraper."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.info(f"[{self.SOURCE_NAME}] Fetching: {url}")
            html = self._get_html_cloudscraper(url, self.LANGUAGE)
            
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /online/{category}/{year}/{month}/{day}/{article_id}
                # Examples: /online/national/2026/01/19/1635439
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
        """Crawl a single article using cloudscraper."""
        if self.storage.is_duplicate(url):
            return None
        
        html = self._get_html_cloudscraper(url, self.LANGUAGE)
        if not html:
            return None
        
        article = self.parse_article(url, html)
        if article and self.storage.save(article):
            self.progress.add_crawled_url(self.SOURCE_NAME, url)
            return article
        
        return None
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body_parts = []
            content_div = soup.find("div", class_=re.compile(r"news-content|article-content|single-news", re.I))
            
            if content_div:
                for p in content_div.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        body_parts.append(text)
            
            body = "\n\n".join(body_parts)
            if len(body) < 50:
                return None
            
            date = self._extract_date(soup)
            category = self._extract_category_from_url(url)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=date,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
            )
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None


# Registry of cloudscraper-based crawlers
CLOUDSCRAPER_CRAWLERS = {
    "daily_sun": DailySunCloudCrawler,
    "bdnews24": BDNews24CloudCrawler,
    "kaler_kantho": KalerKanthoCloudCrawler,
}
