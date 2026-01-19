"""
Prothom Alo API-based Crawler.

Uses the official Prothom Alo API to fetch articles directly.
API endpoint: https://www.prothomalo.com/api/v1/collections/latest-all
"""

import logging
import time
from typing import Optional, Generator, List, Dict, Any

import requests

from .models import Article
from .storage import ArticleStorage

logger = logging.getLogger(__name__)


class ProthomAloAPICrawler:
    """
    API-based crawler for Prothom Alo.
    
    Uses the public API which has 1.3M+ articles available.
    """
    
    SOURCE_NAME = "prothom_alo"
    LANGUAGE = "bn"
    BASE_URL = "https://www.prothomalo.com"
    API_URL = "https://www.prothomalo.com/api/v1/collections/latest-all"
    
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
            "Accept": "application/json",
        })
    
    def fetch_articles(
        self,
        offset: int = 0,
        limit: int = 50,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch articles from the API.
        
        Args:
            offset: Starting position
            limit: Number of articles to fetch (max 50)
        
        Returns:
            API response as dict or None on error
        """
        params = {
            "item-type": "story",
            "offset": offset,
            "limit": min(limit, 50),  # API max is 50
        }
        
        try:
            response = self.session.get(self.API_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
    
    def parse_article(self, item: Dict[str, Any]) -> Optional[Article]:
        """
        Parse an article from API response item.
        
        Args:
            item: Single item from API response
        
        Returns:
            Article object or None
        """
        try:
            story = item.get("story", {})
            if not story:
                return None
            
            # Get headline
            headline = story.get("headline", "")
            if not headline:
                return None
            
            # Get URL
            url = story.get("url", "")
            if not url:
                slug = story.get("slug", "")
                if slug:
                    url = f"{self.BASE_URL}/{slug}"
                else:
                    return None
            
            # Skip if duplicate
            if self.storage.is_duplicate(url):
                return None
            
            # Extract body from cards
            body_parts = []
            cards = story.get("cards", [])
            for card in cards:
                for element in card.get("story-elements", []):
                    if element.get("type") == "text":
                        text = element.get("text", "")
                        # Remove HTML tags
                        import re
                        clean_text = re.sub(r"<[^>]+>", "", text)
                        if clean_text and len(clean_text) > 20:
                            body_parts.append(clean_text)
            
            body = "\n\n".join(body_parts)
            
            # If no body from cards, try summary/excerpt
            if len(body) < 100:
                summary = story.get("summary") or story.get("seo", {}).get("meta-description", "")
                if summary:
                    body = summary
            
            # Skip short articles
            if len(body) < 50:
                return None
            
            # Get date
            published_at = story.get("published-at")
            if published_at:
                # Convert timestamp to ISO format
                from datetime import datetime
                date = datetime.fromtimestamp(published_at / 1000).isoformat()
            else:
                date = None
            
            # Get category from sections
            sections = story.get("sections", [])
            category = sections[0].get("slug", "general") if sections else "general"
            
            return Article(
                url=url,
                title=headline,
                body=body,
                date=date,
                language=self.LANGUAGE,
                source=self.SOURCE_NAME,
                category=category,
            )
        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None
    
    def crawl(self, limit: int = 500) -> int:
        """
        Crawl articles using the API.
        
        Args:
            limit: Maximum number of articles to crawl
        
        Returns:
            Number of articles crawled
        """
        logger.info(f"[{self.SOURCE_NAME}] Starting API crawl (limit: {limit})")
        
        total_crawled = 0
        offset = 0
        batch_size = 50  # API max per request
        consecutive_failures = 0
        max_failures = 3
        
        while total_crawled < limit:
            # Fetch batch
            logger.info(f"[{self.SOURCE_NAME}] Fetching offset {offset}...")
            data = self.fetch_articles(offset=offset, limit=batch_size)
            
            if not data:
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    logger.error(f"[{self.SOURCE_NAME}] Too many failures, stopping")
                    break
                time.sleep(2)
                continue
            
            consecutive_failures = 0
            items = data.get("items", [])
            
            if not items:
                logger.info(f"[{self.SOURCE_NAME}] No more articles available")
                break
            
            # Process articles
            for item in items:
                if total_crawled >= limit:
                    break
                
                article = self.parse_article(item)
                if article and self.storage.save(article):
                    total_crawled += 1
                    title_preview = article.title[:40] if len(article.title) > 40 else article.title
                    logger.info(f"[{self.SOURCE_NAME}][{total_crawled}/{limit}] {title_preview}...")
            
            # Move to next batch
            offset += batch_size
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"[{self.SOURCE_NAME}] Finished. Total: {total_crawled} articles")
        return total_crawled


def crawl_prothom_alo_api(limit: int = 500) -> int:
    """
    Convenience function to crawl Prothom Alo using the API.
    """
    crawler = ProthomAloAPICrawler()
    return crawler.crawl(limit=limit)
