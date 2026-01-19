"""
Prothom Alo (Bangla) news crawler using RSS/Atom feed.
"""

import re
import logging
from typing import List, Optional, Generator, Set
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from .models import Article
from .http_client import HttpClient
from .storage import ArticleStorage, CrawlProgress
from .config import (
    PROTHOM_ALO_BASE_URL,
    PROTHOM_ALO_OUTPUT,
    MAX_ARTICLES_PER_CATEGORY,
)

logger = logging.getLogger(__name__)


class ProthomAloCrawler:
    """
    Crawler for Prothom Alo (Bangla news).
    
    Strategy:
    1. Use RSS/Atom feed to discover article URLs (bypasses JavaScript rendering)
    2. Crawl individual article pages for full content
    3. Handle UTF-8 encoding for Bangla text
    4. Save to JSON Lines storage
    """
    
    SOURCE_NAME = "prothomalo"
    LANGUAGE = "bn"
    FEED_URL = "https://www.prothomalo.com/feed"
    
    # Category-specific feeds
    CATEGORY_FEEDS = {
        "bangladesh": "https://www.prothomalo.com/feed?collection=bangladesh",
        "politics": "https://www.prothomalo.com/feed?collection=politics",
        "world": "https://www.prothomalo.com/feed?collection=world",
        "business": "https://www.prothomalo.com/feed?collection=business",
        "sports": "https://www.prothomalo.com/feed?collection=sports",
        "entertainment": "https://www.prothomalo.com/feed?collection=entertainment",
        "opinion": "https://www.prothomalo.com/feed?collection=opinion",
    }
    
    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        storage: Optional[ArticleStorage] = None,
    ):
        self.client = http_client or HttpClient()
        self.storage = storage or ArticleStorage(PROTHOM_ALO_OUTPUT)
        self.progress = CrawlProgress()
        self.base_url = PROTHOM_ALO_BASE_URL
        self._seen_urls: Set[str] = set()
    
    def discover_article_urls_from_feed(
        self,
        feed_url: Optional[str] = None,
        max_articles: int = 500,
    ) -> Generator[str, None, None]:
        """
        Discover article URLs from the RSS/Atom feed.
        
        Args:
            feed_url: Feed URL (default: main feed)
            max_articles: Maximum number of URLs to yield
        
        Yields:
            Article URLs
        """
        feed_url = feed_url or self.FEED_URL
        
        logger.info(f"Fetching feed: {feed_url}")
        
        xml_content = self.client.get(feed_url, language=self.LANGUAGE)
        if not xml_content:
            logger.warning(f"Failed to fetch feed: {feed_url}")
            return
        
        try:
            # Parse Atom feed
            root = ET.fromstring(xml_content)
            
            # Handle Atom namespace
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            # Find all entry elements
            entries = root.findall('.//atom:entry', ns)
            if not entries:
                # Try without namespace
                entries = root.findall('.//entry')
            
            count = 0
            for entry in entries:
                if count >= max_articles:
                    break
                
                # Get link href
                link = entry.find('atom:link', ns)
                if link is None:
                    link = entry.find('link')
                
                if link is not None:
                    href = link.get('href', '')
                    
                    # Filter for article URLs (skip video, photo, etc.)
                    if href and self._is_article_url(href):
                        if href not in self._seen_urls:
                            self._seen_urls.add(href)
                            count += 1
                            yield href
            
            logger.info(f"Found {count} article URLs from feed")
            
        except ET.ParseError as e:
            logger.error(f"Error parsing feed XML: {e}")
    
    def _is_article_url(self, href: str) -> bool:
        """
        Check if a URL is a valid Prothom Alo article URL.
        Filters out video, photo, and other non-article content.
        """
        if not href:
            return False
        
        # Skip non-article paths
        skip_patterns = ["/video/", "/photo/", "/quiz/", "/collection/", 
                         "/iframe", "/api/", "/author/", "/topic/"]
        for pattern in skip_patterns:
            if pattern in href:
                return False
        
        # Must be from prothomalo.com
        if not href.startswith(self.base_url):
            return False
        
        # Must end with alphanumeric slug (8-12 chars)
        if re.search(r'/[a-z0-9]{8,12}$', href):
            return True
        
        return False
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """
        Parse Bangla article content from HTML.
        
        Args:
            url: Article URL
            html: Raw HTML content
        
        Returns:
            Article object or None if parsing failed
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # Extract title (Bangla)
            title = None
            
            # Try h1 first
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)
            
            # Fallback to og:title
            if not title:
                og_title = soup.find("meta", property="og:title")
                if og_title:
                    title = og_title.get("content", "").strip()
                    # Remove site name suffix
                    title = re.sub(r"\s*\|\s*প্রথম আলো$", "", title)
            
            if not title:
                logger.warning(f"No title found for {url}")
                return None
            
            # Extract body text (Bangla)
            body_parts = []
            
            # Method 1: Use story-element-text class (most accurate)
            story_elements = soup.find_all("div", class_=re.compile(r"story-element.*text", re.I))
            for elem in story_elements:
                for p in elem.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:
                        body_parts.append(text)
            
            # Method 2: Look for article or main content container
            if not body_parts:
                article_body = soup.find("article") or soup.find("div", class_=re.compile(r"story-content|article-content", re.I))
                if article_body:
                    for p in article_body.find_all("p"):
                        text = p.get_text(strip=True)
                        if text and (len(text) > 20 or self._contains_bangla(text)):
                            body_parts.append(text)
            
            # Method 3: Fallback - get paragraphs from page
            if not body_parts:
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    # Filter: must have Bangla or substantial content
                    if text and len(text) > 30 and self._contains_bangla(text):
                        # Skip navigation/footer text
                        if not re.search(r"গুগল নিউজ|ফলো করুন|সাবস্ক্রাইব|প্রথম আলো", text):
                            body_parts.append(text)
            
            body = "\n\n".join(body_parts)
            
            if len(body) < 50:  # Lower threshold for Bangla
                logger.warning(f"Body too short for {url}")
                return None
            
            # Extract date
            date = None
            time_elem = soup.find("time")
            if time_elem:
                date = time_elem.get("datetime") or time_elem.get_text(strip=True)
            
            if not date:
                date_meta = soup.find("meta", property="article:published_time")
                if date_meta:
                    date = date_meta.get("content")
            
            # Extract category from URL
            category = "general"
            url_parts = url.replace(self.base_url, "").strip("/").split("/")
            if url_parts:
                category = url_parts[0]
            
            # Extract tags (Bangla topics)
            tags = []
            tag_links = soup.find_all("a", href=re.compile(r"/topic/"))
            for tag_link in tag_links[:10]:
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
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def _contains_bangla(self, text: str) -> bool:
        """Check if text contains Bangla characters."""
        # Bangla Unicode range: U+0980 to U+09FF
        return bool(re.search(r"[\u0980-\u09FF]", text))
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """
        Crawl a single Bangla article.
        
        Args:
            url: Article URL
        
        Returns:
            Article object or None if failed
        """
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
        limit: int = 2500,
        categories: Optional[List[str]] = None,
    ) -> int:
        """
        Crawl articles from Prothom Alo using RSS feeds.
        
        Args:
            limit: Maximum number of articles to crawl
            categories: Categories to crawl (default: all available)
        
        Returns:
            Number of articles crawled
        """
        categories = categories or list(self.CATEGORY_FEEDS.keys())
        articles_per_category = min(MAX_ARTICLES_PER_CATEGORY, limit // len(categories) + 1)
        
        total_crawled = 0
        
        # First, try the main feed
        logger.info("Crawling from main feed...")
        for article_url in self.discover_article_urls_from_feed(max_articles=limit):
            if total_crawled >= limit:
                break
            
            article = self.crawl_article(article_url)
            if article:
                total_crawled += 1
                title_preview = article.title[:30] if len(article.title) > 30 else article.title
                logger.info(f"[{total_crawled}/{limit}] Crawled: {title_preview}...")
        
        # If we need more, try category feeds
        if total_crawled < limit:
            for category in categories:
                if total_crawled >= limit:
                    break
                
                if category in self.CATEGORY_FEEDS:
                    feed_url = self.CATEGORY_FEEDS[category]
                    logger.info(f"Crawling category feed: {category}")
                    
                    category_count = 0
                    for article_url in self.discover_article_urls_from_feed(
                        feed_url=feed_url,
                        max_articles=articles_per_category
                    ):
                        if category_count >= articles_per_category or total_crawled >= limit:
                            break
                        
                        article = self.crawl_article(article_url)
                        if article:
                            total_crawled += 1
                            category_count += 1
                            title_preview = article.title[:30] if len(article.title) > 30 else article.title
                            logger.info(f"[{total_crawled}/{limit}] Crawled: {title_preview}...")
        
        logger.info(f"Finished crawling Prothom Alo. Total: {total_crawled} articles")
        return total_crawled
