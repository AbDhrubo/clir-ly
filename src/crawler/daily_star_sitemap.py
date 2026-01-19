"""
Daily Star Sitemap-based Crawler.

Uses the paginated sitemap at /sitemap.xml?page=N to discover article URLs.
"""

import logging
import time
import re
import xml.etree.ElementTree as ET
from typing import Optional, List

import requests
from bs4 import BeautifulSoup

from .models import Article
from .storage import ArticleStorage

logger = logging.getLogger(__name__)


class DailyStarSitemapCrawler:
    """
    Sitemap-based crawler for The Daily Star.
    
    Uses paginated sitemap to discover and crawl articles.
    """
    
    SOURCE_NAME = "daily_star"
    LANGUAGE = "en"
    BASE_URL = "https://www.thedailystar.net"
    SITEMAP_URL = "https://www.thedailystar.net/sitemap.xml"
    
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
    
    def get_sitemap_page(self, page: int) -> Optional[str]:
        """
        Fetch sitemap page.
        
        Args:
            page: Page number
        
        Returns:
            XML content or None on error
        """
        url = f"{self.SITEMAP_URL}?page={page}"
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch sitemap page {page}: {e}")
            return None
    
    def extract_urls_from_sitemap(self, xml_content: str) -> List[str]:
        """
        Extract article URLs from sitemap XML.
        
        Args:
            xml_content: Sitemap XML
        
        Returns:
            List of article URLs
        """
        urls = []
        try:
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Handle namespace
            ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            
            # Find all loc elements
            for url_elem in root.findall(".//ns:url/ns:loc", ns):
                if url_elem.text:
                    url = url_elem.text
                    # Only include news article URLs (contain numeric ID)
                    if re.search(r'-\d+$', url):
                        urls.append(url)
        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap XML: {e}")
        
        return urls
    
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
                ".article-content",
                "article",
                ".story-body",
                ".content-body",
            ]
            
            for selector in content_selectors:
                content_div = soup.select_one(selector)
                if content_div:
                    for p in content_div.find_all("p"):
                        text = p.get_text(strip=True)
                        if text and len(text) > 20:
                            body_parts.append(text)
                    break
            
            # Fallback: get all paragraphs
            if not body_parts:
                for p in soup.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 50:
                        body_parts.append(text)
            
            body = "\n\n".join(body_parts)
            
            # Skip short articles
            if len(body) < 100:
                return None
            
            # Extract date
            date = None
            date_meta = soup.find("meta", {"property": "article:published_time"})
            if date_meta:
                date = date_meta.get("content")
            
            # Extract category from URL
            url_parts = url.replace(self.BASE_URL, "").strip("/").split("/")
            category = url_parts[0] if url_parts else "general"
            
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
    
    def crawl(self, limit: int = 1000, max_sitemap_pages: int = 20) -> int:
        """
        Crawl articles from sitemap pages.
        
        Args:
            limit: Maximum number of articles to crawl
            max_sitemap_pages: Maximum sitemap pages to process
        
        Returns:
            Number of articles crawled
        """
        logger.info(f"[{self.SOURCE_NAME}] Starting sitemap crawl (limit: {limit})")
        
        total_crawled = 0
        
        for page in range(1, max_sitemap_pages + 1):
            if total_crawled >= limit:
                break
            
            logger.info(f"[{self.SOURCE_NAME}] Processing sitemap page {page}...")
            
            xml_content = self.get_sitemap_page(page)
            if not xml_content:
                break
            
            urls = self.extract_urls_from_sitemap(xml_content)
            logger.info(f"[{self.SOURCE_NAME}] Found {len(urls)} URLs on sitemap page {page}")
            
            if not urls:
                break  # No more URLs
            
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
            
            # Pause between pages
            time.sleep(0.5)
        
        logger.info(f"[{self.SOURCE_NAME}] Finished. Total: {total_crawled} articles")
        return total_crawled


def crawl_daily_star_sitemap(limit: int = 1000, max_pages: int = 20) -> int:
    """
    Convenience function to crawl Daily Star sitemap.
    """
    crawler = DailyStarSitemapCrawler()
    return crawler.crawl(limit=limit, max_sitemap_pages=max_pages)
