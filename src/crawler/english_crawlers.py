"""
English news site crawlers.

Sites:
- The Daily Star (thedailystar.net)
- New Age (newagebd.net)
- Dhaka Tribune (dhakatribune.com)
- Daily Sun (daily-sun.com)
- The New Nation (dailynewnation.com)
"""

import re
import logging
from typing import Optional, Generator, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from .models import Article

logger = logging.getLogger(__name__)


class DailyStarCrawler(BaseCrawler):
    """Crawler for The Daily Star (English)."""
    
    SOURCE_NAME = "daily_star"
    LANGUAGE = "en"
    BASE_URL = "https://www.thedailystar.net"
    CATEGORIES = [
        "/news/bangladesh",
        "/news/bangladesh/politics",
        "/business",
        "/sports",
        "/entertainment",
        "/lifestyle",
        "/opinion",
        "/world",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        start_page = self.progress.get_last_page(self.SOURCE_NAME, category)
        
        for page in range(start_page, start_page + max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            logger.debug(f"Fetching category page: {url}")
            
            html = self.client.get(url)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match Daily Star article URLs ending with -numeric_id
                # Example: /news/bangladesh/politics/news/article-title-4084481
                if re.search(r"-\d{5,}$", href) and "/news/" in href:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
            
            self.progress.set_last_page(self.SOURCE_NAME, category, page + 1)
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            # Daily Star specific body extraction
            body = self._extract_body(soup, [
                "article",
                "div.article-content",
                "div.field-body",
            ])
            
            if len(body) < 100:
                return None
            
            date = self._extract_date(soup)
            category = self._extract_category_from_url(url)
            
            # Extract tags
            tags = []
            for tag_link in soup.find_all("a", href=re.compile(r"/tags/")):
                tag_text = tag_link.get_text(strip=True)
                if tag_text:
                    tags.append(tag_text)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=date,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
                tags=tags[:10],
            )
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None


class NewAgeCrawler(BaseCrawler):
    """Crawler for New Age (English)."""
    
    SOURCE_NAME = "newage"
    LANGUAGE = "en"
    BASE_URL = "https://www.newagebd.net"
    # Category format: /articlelist/{id}/{name}
    CATEGORIES = [
        "/articlelist/42/Politics",
        "/articlelist/49/Country",
        "/articlelist/29/business-economy",
        "/articlelist/31/world",
        "/articlelist/22/sports",
        "/articlelist/25/editorial",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        # New Age uses format: /post/{category}/{id}/{slug}
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            html = self.client.get(url)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /post/{category}/{numeric_id}/{slug}
                if re.search(r"/post/[^/]+/\d+/", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls:
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body = self._extract_body(soup, [
                "div.news-details",
                "div.article-content",
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


class DhakaTribuneCrawler(BaseCrawler):
    """Crawler for Dhaka Tribune (English)."""
    
    SOURCE_NAME = "dhaka_tribune"
    LANGUAGE = "en"
    BASE_URL = "https://www.dhakatribune.com"
    CATEGORIES = [
        "/bangladesh/politics",
        "/bangladesh/nation",
        "/business",
        "/sport",
        "/world",
        "/opinion",
        "/feature",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        # Dhaka Tribune uses: /{category}/{id}/{slug}
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            html = self.client.get(url)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{numeric_id}/{slug}
                if re.search(r"/\d{4,}/", href) and not "/video/" in href:
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body = self._extract_body(soup, [
                "div.story-body",
                "div.article-content",
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


class DailySunCrawler(BaseCrawler):
    """
    Crawler for Daily Sun (English).
    Note: Site uses Cloudflare protection - may require special headers.
    """
    
    SOURCE_NAME = "daily_sun"
    LANGUAGE = "en"
    BASE_URL = "https://www.daily-sun.com"
    # Pattern: /{category}/{id}/{slug}
    CATEGORIES = [
        "/bangladesh",
        "/politics",
        "/business",
        "/sports",
        "/world",
        "/opinion",
        "/entertainment",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            # Note: Daily Sun has Cloudflare protection
            html = self.client.get(url, language=self.LANGUAGE)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{numeric_id}/{slug}
                if re.search(r"/\d{6}/[a-z0-9-]+", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body = self._extract_body(soup, [
                "div.news-details",
                "div.article-content",
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


class NewNationCrawler(BaseCrawler):
    """Crawler for The New Nation (English)."""
    
    SOURCE_NAME = "new_nation"
    LANGUAGE = "en"
    BASE_URL = "https://dailynewnation.com"  # No 'www'
    # Category format: /news/category/todays-news/{category}/
    CATEGORIES = [
        "/news/category/todays-news/national/",
        "/news/category/todays-news/international/",
        "/news/category/todays-news/city/",
        "/news/category/todays-news/sports/",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}page/{page}/"
            
            html = self.client.get(url)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /news/{numeric_id}/
                if re.search(r"/news/\d{6,}/", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            if found == 0:
                break
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body = self._extract_body(soup, [
                "div.entry-content",
                "div.article-content",
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


# Registry of all English crawlers
ENGLISH_CRAWLERS = {
    "daily_star": DailyStarCrawler,
    "newage": NewAgeCrawler,
    "dhaka_tribune": DhakaTribuneCrawler,
    "daily_sun": DailySunCrawler,
    "new_nation": NewNationCrawler,
}
