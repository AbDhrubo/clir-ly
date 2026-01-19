"""
The Daily Star (English) news crawler.
"""

import re
import logging
from typing import List, Optional, Generator
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .models import Article
from .http_client import HttpClient
from .storage import ArticleStorage, CrawlProgress
from .config import (
    DAILY_STAR_BASE_URL,
    DAILY_STAR_CATEGORIES,
    DAILY_STAR_OUTPUT,
    MAX_ARTICLES_PER_CATEGORY,
)

logger = logging.getLogger(__name__)


class DailyStarCrawler:
    """
    Crawler for The Daily Star (English news).
    
    Strategy:
    1. Crawl category pages to discover article URLs
    2. For each article, extract title, body, date
    3. Save to JSON Lines storage
    """
    
    SOURCE_NAME = "thedailystar"
    LANGUAGE = "en"
    
    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        storage: Optional[ArticleStorage] = None,
    ):
        self.client = http_client or HttpClient()
        self.storage = storage or ArticleStorage(DAILY_STAR_OUTPUT)
        self.progress = CrawlProgress()
        self.base_url = DAILY_STAR_BASE_URL
    
    def discover_article_urls(
        self,
        category: str,
        max_pages: int = 10,
    ) -> Generator[str, None, None]:
        """
        Discover article URLs from a category page.
        
        Args:
            category: Category path (e.g., '/news/bangladesh')
            max_pages: Maximum number of pages to crawl
        
        Yields:
            Article URLs
        """
        start_page = self.progress.get_last_page(self.SOURCE_NAME, category)
        
        for page in range(start_page, start_page + max_pages):
            # Construct category page URL
            if page == 0:
                url = f"{self.base_url}{category}"
            else:
                url = f"{self.base_url}{category}?page={page}"
            
            logger.info(f"Discovering articles from: {url}")
            
            html = self.client.get(url, language=self.LANGUAGE)
            if not html:
                logger.warning(f"Failed to fetch category page: {url}")
                break
            
            soup = BeautifulSoup(html, "lxml")
            
            # Find article links
            # Daily Star uses various article link patterns
            article_links = []
            
            # Pattern 1: Links containing /news/ with article IDs
            for link in soup.find_all("a", href=True):
                href = link["href"]
                # Match article URLs (contain /news/ and end with numbers or slug)
                if re.search(r"/news/.*-\d+$", href) or re.search(r"/(news|business|sports|opinion|environment)/.*/.+-\d+", href):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in article_links:
                        article_links.append(full_url)
            
            if not article_links:
                logger.info(f"No more articles found on page {page}")
                break
            
            for article_url in article_links:
                yield article_url
            
            # Update progress
            self.progress.set_last_page(self.SOURCE_NAME, category, page + 1)
    
    def parse_article(self, url: str, html: str) -> Optional[Article]:
        """
        Parse article content from HTML.
        
        Args:
            url: Article URL
            html: Raw HTML content
        
        Returns:
            Article object or None if parsing failed
        """
        try:
            soup = BeautifulSoup(html, "lxml")
            
            # Extract title
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
            
            if not title:
                logger.warning(f"No title found for {url}")
                return None
            
            # Extract body text
            body_parts = []
            
            # Try to find article body container
            article_body = soup.find("article") or soup.find("div", class_=re.compile(r"article|content|body", re.I))
            
            if article_body:
                # Get all paragraphs
                for p in article_body.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # Skip short fragments
                        body_parts.append(text)
            else:
                # Fallback: get all paragraphs from main content
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    # Filter out navigation, footer, etc.
                    if text and len(text) > 50 and not re.search(r"copyright|subscribe|newsletter|login", text, re.I):
                        body_parts.append(text)
            
            body = "\n\n".join(body_parts)
            
            if len(body) < 100:
                logger.warning(f"Body too short for {url}")
                return None
            
            # Extract date
            date = None
            # Try various date selectors
            time_elem = soup.find("time")
            if time_elem:
                date = time_elem.get("datetime") or time_elem.get_text(strip=True)
            
            # Try meta tag
            if not date:
                date_meta = soup.find("meta", property="article:published_time")
                if date_meta:
                    date = date_meta.get("content")
            
            # Extract category from URL
            category = "general"
            url_parts = url.split("/")
            for i, part in enumerate(url_parts):
                if part in ["news", "business", "sports", "opinion", "environment", "tech-startup"]:
                    if i + 1 < len(url_parts) and url_parts[i + 1] not in ["news"]:
                        category = url_parts[i + 1] if part == "news" else part
                    else:
                        category = part
                    break
            
            # Extract tags
            tags = []
            tag_links = soup.find_all("a", href=re.compile(r"/tags/"))
            for tag_link in tag_links[:10]:  # Limit to 10 tags
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
                tags=tags,
            )
            
        except Exception as e:
            logger.error(f"Error parsing article {url}: {e}")
            return None
    
    def crawl_article(self, url: str) -> Optional[Article]:
        """
        Crawl a single article.
        
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
        Crawl articles from The Daily Star.
        
        Args:
            limit: Maximum number of articles to crawl
            categories: Categories to crawl (default: all)
        
        Returns:
            Number of articles crawled
        """
        categories = categories or DAILY_STAR_CATEGORIES
        articles_per_category = min(MAX_ARTICLES_PER_CATEGORY, limit // len(categories) + 1)
        
        total_crawled = 0
        
        for category in categories:
            if total_crawled >= limit:
                break
            
            logger.info(f"Crawling category: {category}")
            category_count = 0
            
            for article_url in self.discover_article_urls(category):
                if category_count >= articles_per_category or total_crawled >= limit:
                    break
                
                article = self.crawl_article(article_url)
                if article:
                    total_crawled += 1
                    category_count += 1
                    logger.info(f"[{total_crawled}/{limit}] Crawled: {article.title[:50]}...")
        
        logger.info(f"Finished crawling The Daily Star. Total: {total_crawled} articles")
        return total_crawled
