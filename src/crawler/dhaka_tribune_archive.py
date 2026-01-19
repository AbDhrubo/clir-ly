"""
Dhaka Tribune Archive-based Crawler.

Uses the date-based archive pages at /archive/YYYY-MM-DD to discover articles.
"""

import logging
import time
import re
from datetime import datetime, timedelta
from typing import Optional, List, Set

import requests
from bs4 import BeautifulSoup

from .models import Article
from .storage import ArticleStorage

logger = logging.getLogger(__name__)


class DhakaTribuneArchiveCrawler:
    """
    Archive-based crawler for Dhaka Tribune.
    
    Uses date-based archive pages to discover and crawl articles.
    """
    
    SOURCE_NAME = "dhaka_tribune"
    LANGUAGE = "en"
    BASE_URL = "https://www.dhakatribune.com"
    ARCHIVE_URL = "https://www.dhakatribune.com/archive"
    
    def __init__(
        self,
        storage: Optional[ArticleStorage] = None,
        output_path: Optional[str] = None,
    ):
        self.storage = storage or ArticleStorage(
            output_path or f"data/raw/{self.SOURCE_NAME}_articles.jsonl"
        )
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml",
        })
    
    def get_archive_page(self, date_str: str) -> Optional[str]:
        """
        Fetch archive page for a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format
        
        Returns:
            HTML content or None on error
        """
        url = f"{self.ARCHIVE_URL}/{date_str}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch archive for {date_str}: {e}")
            return None
    
    def extract_article_urls(self, html: str) -> List[str]:
        """
        Extract article URLs from archive page HTML.
        
        Args:
            html: Archive page HTML
        
        Returns:
            List of article URLs
        """
        soup = BeautifulSoup(html, "lxml")
        urls = []
        
        # Find all article links in the archive
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Match article URLs like /bangladesh/401304/article-slug
            if re.match(r"^//www\.dhakatribune\.com/[^/]+/\d+/", href):
                url = "https:" + href
                urls.append(url)
            elif re.match(r"^/[^/]+/\d+/", href):
                url = self.BASE_URL + href
                urls.append(url)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def extract_article(self, url: str) -> Optional[Article]:
        """
        Extract article content from URL.
        
        Args:
            url: Article URL
        
        Returns:
            Article object or None
        """
        # Skip if duplicate
        if self.storage.is_duplicate(url):
            return None
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            
            # Extract title
            title_el = soup.find("h1")
            if not title_el:
                return None
            title = title_el.get_text(strip=True)
            
            # Extract body from article content
            body_parts = []
            
            # Try different content selectors
            content_selectors = [
                ".jw_detail_content_holder",
                ".content_detail",
                "article",
                ".article-body",
            ]
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    for p in content_div.find_all("p"):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            body_parts.append(text)
                    break
            
            body = "\n\n".join(body_parts)
            
            # Skip short articles
            if len(body) < 100:
                return None
            
            # Extract date from URL or meta
            date = None
            date_meta = soup.find("meta", {"property": "article:published_time"})
            if date_meta:
                date = date_meta.get("content")
            
            # Extract category from URL
            url_parts = url.replace(self.BASE_URL, "").split("/")
            category = url_parts[1] if len(url_parts) > 1 else "general"
            
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
            logger.error(f"Error extracting article {url}: {e}")
            return None
    
    def crawl(self, limit: int = 500, days_back: int = 30) -> int:
        """
        Crawl articles from archive pages.
        
        Args:
            limit: Maximum number of articles to crawl
            days_back: Number of days to go back in archive
        
        Returns:
            Number of articles crawled
        """
        logger.info(f"[{self.SOURCE_NAME}] Starting archive crawl (limit: {limit}, days: {days_back})")
        
        total_crawled = 0
        current_date = datetime.now()
        
        for day_offset in range(days_back):
            if total_crawled >= limit:
                break
            
            target_date = current_date - timedelta(days=day_offset)
            date_str = target_date.strftime("%Y-%m-%d")
            
            logger.info(f"[{self.SOURCE_NAME}] Crawling archive for {date_str}...")
            
            html = self.get_archive_page(date_str)
            if not html:
                continue
            
            urls = self.extract_article_urls(html)
            logger.info(f"[{self.SOURCE_NAME}] Found {len(urls)} articles for {date_str}")
            
            for url in urls:
                if total_crawled >= limit:
                    break
                
                article = self.extract_article(url)
                if article and self.storage.save(article):
                    total_crawled += 1
                    title_preview = article.title[:40] if len(article.title) > 40 else article.title
                    logger.info(f"[{self.SOURCE_NAME}][{total_crawled}/{limit}] {title_preview}...")
                
                # Rate limiting
                time.sleep(0.3)
            
            # Pause between days
            time.sleep(0.5)
        
        logger.info(f"[{self.SOURCE_NAME}] Finished. Total: {total_crawled} articles")
        return total_crawled


def crawl_dhaka_tribune_archive(limit: int = 500, days_back: int = 30) -> int:
    """
    Convenience function to crawl Dhaka Tribune archive.
    """
    crawler = DhakaTribuneArchiveCrawler()
    return crawler.crawl(limit=limit, days_back=days_back)
