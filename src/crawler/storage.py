"""
Storage utilities for persisting crawled articles.
"""

import json
import logging
from pathlib import Path
from typing import Set, Iterator, Optional

from .models import Article
from .config import CRAWL_PROGRESS_FILE

logger = logging.getLogger(__name__)


class ArticleStorage:
    """
    JSON Lines storage for articles with deduplication and resume support.
    
    Format: One JSON object per line (.jsonl)
    """
    
    def __init__(self, output_path: Path):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Track seen URLs for deduplication
        self._seen_urls: Set[str] = set()
        self._load_existing_urls()
    
    def _load_existing_urls(self):
        """Load URLs from existing file for deduplication."""
        if not self.output_path.exists():
            return
        
        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            self._seen_urls.add(data.get("url", ""))
                        except json.JSONDecodeError:
                            continue
            
            logger.info(f"Loaded {len(self._seen_urls)} existing URLs from {self.output_path}")
        except Exception as e:
            logger.error(f"Error loading existing URLs: {e}")
    
    def is_duplicate(self, url: str) -> bool:
        """Check if URL has already been crawled."""
        return url in self._seen_urls
    
    def save(self, article: Article) -> bool:
        """
        Save an article to storage.
        
        Returns:
            True if saved successfully, False if duplicate or invalid
        """
        if not article.is_valid():
            logger.warning(f"Skipping invalid article: {article.url}")
            return False
        
        if self.is_duplicate(article.url):
            logger.debug(f"Skipping duplicate: {article.url}")
            return False
        
        try:
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(article.to_json() + "\n")
            
            self._seen_urls.add(article.url)
            return True
            
        except Exception as e:
            logger.error(f"Error saving article {article.url}: {e}")
            return False
    
    def count(self) -> int:
        """Return number of stored articles."""
        return len(self._seen_urls)
    
    def iter_articles(self) -> Iterator[Article]:
        """Iterate over all stored articles."""
        if not self.output_path.exists():
            return
        
        with open(self.output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        yield Article.from_json(line)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Error parsing article: {e}")
                        continue
    
    def get_all_articles(self) -> list:
        """Load all articles into memory."""
        return list(self.iter_articles())


class CrawlProgress:
    """
    Track crawling progress for resume capability.
    """
    
    def __init__(self, progress_file: Path = CRAWL_PROGRESS_FILE):
        self.progress_file = Path(progress_file)
        self._progress = self._load()
    
    def _load(self) -> dict:
        """Load progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save(self):
        """Save progress to file."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self._progress, f, indent=2)
    
    def get_last_page(self, source: str, category: str) -> int:
        """Get last crawled page for a source/category."""
        key = f"{source}:{category}"
        return self._progress.get(key, {}).get("last_page", 0)
    
    def set_last_page(self, source: str, category: str, page: int):
        """Update last crawled page."""
        key = f"{source}:{category}"
        if key not in self._progress:
            self._progress[key] = {}
        self._progress[key]["last_page"] = page
        self._save()
    
    def get_crawled_urls(self, source: str) -> Set[str]:
        """Get set of crawled URLs for a source."""
        return set(self._progress.get(f"{source}:urls", []))
    
    def add_crawled_url(self, source: str, url: str):
        """Mark a URL as crawled."""
        key = f"{source}:urls"
        if key not in self._progress:
            self._progress[key] = []
        if url not in self._progress[key]:
            self._progress[key].append(url)
        # Save periodically (every 50 URLs)
        if len(self._progress[key]) % 50 == 0:
            self._save()
    
    def clear(self, source: Optional[str] = None):
        """Clear progress for a source or all sources."""
        if source:
            keys_to_remove = [k for k in self._progress if k.startswith(source)]
            for key in keys_to_remove:
                del self._progress[key]
        else:
            self._progress = {}
        self._save()
