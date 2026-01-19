"""
Selenium-based crawlers for sites with Cloudflare/WAF protection.

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
from .selenium_client import get_selenium_client, close_selenium_client

logger = logging.getLogger(__name__)

# Register cleanup on exit
atexit.register(close_selenium_client)


class SeleniumCrawlerMixin:
    """Mixin to add Selenium support to crawlers."""
    
    def _get_html_selenium(self, url: str) -> Optional[str]:
        """Fetch HTML using Selenium browser."""
        client = get_selenium_client(headless=True)
        return client.get(url)


class DailySunSeleniumCrawler(BaseCrawler, SeleniumCrawlerMixin):
    """
    Selenium-based crawler for Daily Sun (English).
    Uses browser automation to bypass Cloudflare protection.
    Note: Category pages often blocked, use homepage for discovery.
    """
    
    SOURCE_NAME = "daily_sun"
    LANGUAGE = "en"
    BASE_URL = "https://www.daily-sun.com"
    # Crawl from homepage since category pages are often blocked
    CATEGORIES = ["/"]  # Use homepage
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 1,  # Only one page for homepage
    ) -> Generator[str, None, None]:
        """Discover article URLs from homepage using Selenium."""
        # Always start from homepage (bypasses Cloudflare on category pages)
        url = self.BASE_URL
        
        logger.info(f"[daily_sun] Fetching homepage with Selenium: {url}")
        html = self._get_html_selenium(url)
        
        if not html:
            logger.warning(f"[daily_sun] Failed to fetch homepage")
            return
        
        soup = BeautifulSoup(html, "lxml")
        found = 0
        
        # Log HTML length for debugging
        logger.debug(f"[daily_sun] Retrieved {len(html)} bytes of HTML")
        
        for link in soup.find_all("a", href=True):
            href = link["href"]
            
            # Match: /{category}/{numeric_id}/{slug}
            # Examples: /bangladesh/852534/all-but-2-dual-citizenship-candidates-cleared
            if re.search(r"/(bangladesh|politics|business|sports|world|opinion|entertainment|feature|sun-campus)/\d+/[a-z0-9-]+", href, re.I):
                full_url = urljoin(self.BASE_URL, href)
                if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                    self._seen_urls.add(full_url)
                    found += 1
                    logger.debug(f"[daily_sun] Found article: {full_url}")
                    yield full_url
        
        logger.info(f"[daily_sun] Discovered {found} article URLs from homepage")
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article using Selenium."""
        if self.storage.is_duplicate(url):
            return None
        
        html = self._get_html_selenium(url)
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


class BDNews24SeleniumCrawler(BaseCrawler, SeleniumCrawlerMixin):
    """
    Selenium-based crawler for BD News 24 Bangla.
    Uses browser automation to bypass 403 blocks.
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
        """Discover article URLs using Selenium."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.debug(f"Fetching with Selenium: {url}")
            html = self._get_html_selenium(url)
            
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{hex_id}
                if re.search(r"/[a-f0-9]{12,}$", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article using Selenium."""
        if self.storage.is_duplicate(url):
            return None
        
        html = self._get_html_selenium(url)
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


class KalerKanthoSeleniumCrawler(BaseCrawler, SeleniumCrawlerMixin):
    """
    Selenium-based crawler for Kaler Kantho (Bangla).
    Uses browser automation to bypass 403 blocks.
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
        """Discover article URLs using Selenium."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.debug(f"Fetching with Selenium: {url}")
            html = self._get_html_selenium(url)
            
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match article URLs with numeric IDs
                if re.search(r"/\d{5,}$", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls:
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """Crawl a single article using Selenium."""
        if self.storage.is_duplicate(url):
            return None
        
        html = self._get_html_selenium(url)
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
            content_div = soup.find("div", class_=re.compile(r"news-content|article-content", re.I))
            
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


# Registry of Selenium-based crawlers
SELENIUM_CRAWLERS = {
    "daily_sun": DailySunSeleniumCrawler,
    "bdnews24": BDNews24SeleniumCrawler,
    "kaler_kantho": KalerKanthoSeleniumCrawler,
}
