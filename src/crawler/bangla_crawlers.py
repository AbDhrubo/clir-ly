"""
Bangla news site crawlers.

Sites:
- Prothom Alo (prothomalo.com) - RSS feed based
- BD News 24 (bangla.bdnews24.com)
- Kaler Kantho (kalerkantho.com)
- Bangla Tribune (banglatribune.com)
- Dhaka Post (dhakapost.com)
"""

import re
import logging
import xml.etree.ElementTree as ET
from typing import Optional, Generator, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base_crawler import BaseCrawler
from .models import Article
from .http_client import HttpClient
from .storage import ArticleStorage

logger = logging.getLogger(__name__)


class ProthomAloCrawler(BaseCrawler):
    """
    Crawler for Prothom Alo (Bangla).
    Uses RSS/Atom feed for article discovery since the site is JavaScript-rendered.
    """
    
    SOURCE_NAME = "prothom_alo"
    LANGUAGE = "bn"
    BASE_URL = "https://www.prothomalo.com"
    FEED_URL = "https://www.prothomalo.com/feed"
    CATEGORIES = ["bangladesh", "politics", "world", "business", "sports", "entertainment"]
    
    def discover_article_urls(
        self,
        category: str = None,
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from RSS feed."""
        feed_url = self.FEED_URL
        if category:
            feed_url = f"{self.FEED_URL}?collection={category}"
        
        logger.debug(f"Fetching feed: {feed_url}")
        
        xml_content = self.client.get(feed_url, language=self.LANGUAGE)
        if not xml_content:
            return
        
        try:
            root = ET.fromstring(xml_content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            entries = root.findall('.//atom:entry', ns)
            if not entries:
                entries = root.findall('.//entry')
            
            for entry in entries:
                link = entry.find('atom:link', ns)
                if link is None:
                    link = entry.find('link')
                
                if link is not None:
                    href = link.get('href', '')
                    
                    # Filter valid articles (skip video, photo, etc.)
                    if href and self._is_valid_prothom_alo_url(href):
                        if href not in self._seen_urls:
                            self._seen_urls.add(href)
                            yield href
                            
        except ET.ParseError as e:
            logger.error(f"Error parsing feed XML: {e}")
    
    def _is_valid_prothom_alo_url(self, href: str) -> bool:
        """Check if URL is a valid Prothom Alo article."""
        if not href.startswith(self.BASE_URL):
            return False
        skip = ["/video/", "/photo/", "/quiz/", "/collection/", "/api/"]
        for pattern in skip:
            if pattern in href:
                return False
        # Must end with alphanumeric slug (8-12 chars)
        return bool(re.search(r'/[a-z0-9]{8,12}$', href))
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if title:
                # Remove site suffix
                title = re.sub(r"\s*\|\s*প্রথম আলো$", "", title)
            else:
                return None
            
            # Extract body from story elements
            body_parts = []
            
            # Method 1: story-element-text
            for elem in soup.find_all("div", class_=re.compile(r"story-element.*text", re.I)):
                for p in elem.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:
                        body_parts.append(text)
            
            # Method 2: article or content div
            if not body_parts:
                container = soup.find("article") or soup.find("div", class_=re.compile(r"story-content", re.I))
                if container:
                    for p in container.find_all("p"):
                        text = p.get_text(strip=True)
                        if text and len(text) > 10 and self._contains_bangla(text):
                            body_parts.append(text)
            
            body = "\n\n".join(body_parts)
            if len(body) < 50:
                return None
            
            date = self._extract_date(soup)
            category = self._extract_category_from_url(url)
            
            # Extract tags
            tags = []
            for tag_link in soup.find_all("a", href=re.compile(r"/topic/"))[:10]:
                tag_text = tag_link.get_text(strip=True)
                if tag_text and self._contains_bangla(tag_text):
                    tags.append(tag_text)
            
            return Article(
                url=url,
                title=title,
                body=body,
                date=date,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
                tags=tags,
            )
        except Exception as e:
            logger.error(f"Error parsing {url}: {e}")
            return None
    
    def crawl(self, limit: int = 250, categories: List[str] = None) -> int:
        """Crawl using RSS feed."""
        categories = categories or self.CATEGORIES
        total_crawled = 0
        
        # First, try main feed
        logger.info(f"[{self.SOURCE_NAME}] Crawling from main feed...")
        for article_url in self.discover_article_urls():
            if total_crawled >= limit:
                break
            
            article = self.crawl_article(article_url)
            if article:
                total_crawled += 1
                title_preview = article.title[:40] if len(article.title) > 40 else article.title
                logger.info(f"[{self.SOURCE_NAME}][{total_crawled}/{limit}] {title_preview}...")
        
        # If need more, try category feeds
        if total_crawled < limit:
            for category in categories:
                if total_crawled >= limit:
                    break
                
                logger.info(f"[{self.SOURCE_NAME}] Crawling category: {category}")
                for article_url in self.discover_article_urls(category=category):
                    if total_crawled >= limit:
                        break
                    
                    article = self.crawl_article(article_url)
                    if article:
                        total_crawled += 1
                        title_preview = article.title[:40] if len(article.title) > 40 else article.title
                        logger.info(f"[{self.SOURCE_NAME}][{total_crawled}/{limit}] {title_preview}...")
        
        logger.info(f"[{self.SOURCE_NAME}] Finished. Total: {total_crawled} articles")
        return total_crawled


class BDNews24Crawler(BaseCrawler):
    """Crawler for BD News 24 Bangla."""
    
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
        max_pages: int = 5,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            html = self.client.get(url, language=self.LANGUAGE)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{hex_id} pattern
                if re.search(r"/[a-f0-9]{12,}$", href):
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
            
            body_parts = []
            
            # Find article body
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


class KalerKanthoCrawler(BaseCrawler):
    """
    Crawler for Kaler Kantho (Bangla).
    Note: This site blocks many requests (403). May need special headers.
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
        "/online/entertainment",
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
            
            html = self.client.get(url, language=self.LANGUAGE)
            if not html:
                logger.warning(f"[{self.SOURCE_NAME}] Failed to fetch: {url}")
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
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body_parts = []
            
            # Find article content
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


class BanglaTribuneCrawler(BaseCrawler):
    """Crawler for Bangla Tribune."""
    
    SOURCE_NAME = "bangla_tribune"
    LANGUAGE = "bn"
    BASE_URL = "https://www.banglatribune.com"
    CATEGORIES = [
        "/national",
        "/country",
        "/politics",
        "/foreign",
        "/business",
        "/sport",
        "/entertainment",
    ]
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 3,
    ) -> Generator[str, None, None]:
        """Discover article URLs from category pages."""
        for page in range(max_pages):
            if page == 0:
                url = f"{self.BASE_URL}{category}"
            else:
                url = f"{self.BASE_URL}{category}?page={page}"
            
            html = self.client.get(url, language=self.LANGUAGE)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match: /{category}/{6-digit-id}/{slug}
                # Example: /national/930528/চানখারপুলে-হত্যা-মামলার-রায়
                if re.search(r"/\d{6}/", href):
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url not in self._seen_urls and self._is_valid_article_url(full_url):
                        self._seen_urls.add(full_url)
                        found += 1
                        yield full_url
            
            logger.info(f"[{self.SOURCE_NAME}] Found {found} article URLs from {category}")
            if found == 0:
                break
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """Parse article content."""
        try:
            soup = BeautifulSoup(html, "lxml")
            
            title = self._extract_title(soup)
            if not title:
                return None
            
            body_parts = []
            
            # Find article body
            article = soup.find("article") or soup.find("div", class_=re.compile(r"news-details|content", re.I))
            if article:
                for p in article.find_all("p"):
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


class DhakaPostCrawler(BaseCrawler):
    """Crawler for Dhaka Post (Bangla)."""
    
    SOURCE_NAME = "dhaka_post"
    LANGUAGE = "bn"
    BASE_URL = "https://www.dhakapost.com"
    CATEGORIES = [
        "/national",
        "/politics",
        "/world",
        "/economy",
        "/sports",
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
            
            html = self.client.get(url, language=self.LANGUAGE)
            if not html:
                break
            
            soup = BeautifulSoup(html, "lxml")
            found = 0
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                
                # Match article URLs
                if re.search(r"/[a-z0-9-]+$", href) and len(href) > 30:
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
            
            body_parts = []
            
            # Find article body
            article = soup.find("article") or soup.find("div", class_=re.compile(r"detail|content", re.I))
            if article:
                for p in article.find_all("p"):
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


# Registry of all Bangla crawlers
BANGLA_CRAWLERS = {
    "prothom_alo": ProthomAloCrawler,
    "bdnews24": BDNews24Crawler,
    "kaler_kantho": KalerKanthoCrawler,
    "bangla_tribune": BanglaTribuneCrawler,
    "dhaka_post": DhakaPostCrawler,
}
