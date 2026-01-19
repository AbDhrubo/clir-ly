"""
Duplicate detection and removal for articles.

Handles:
- URL-based exact matching
- Content similarity matching (fuzzy)
- Prefers articles with more recent crawl dates
"""

import re
import hashlib
from typing import List, Dict, Any, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class Deduplicator:
    """Deduplicate articles based on URL and content similarity."""
    
    def __init__(self, 
                 similarity_threshold: float = 0.85,
                 prefer_recent: bool = True):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Jaccard similarity threshold for content matching
            prefer_recent: If True, prefer more recently crawled articles
        """
        self.similarity_threshold = similarity_threshold
        self.prefer_recent = prefer_recent
        self.stats = {
            'url_duplicates': 0,
            'content_duplicates': 0,
            'total_removed': 0,
        }
    
    def deduplicate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate articles.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Deduplicated list of articles
        """
        logger.info(f"Starting deduplication of {len(articles)} articles")
        
        # Reset stats
        self.stats = {'url_duplicates': 0, 'content_duplicates': 0, 'total_removed': 0}
        
        # Step 1: Remove exact URL duplicates
        unique_by_url = self._dedupe_by_url(articles)
        logger.info(f"After URL dedup: {len(unique_by_url)} articles")
        
        # Step 2: Remove content-similar duplicates
        unique_by_content = self._dedupe_by_content(unique_by_url)
        logger.info(f"After content dedup: {len(unique_by_content)} articles")
        
        self.stats['total_removed'] = len(articles) - len(unique_by_content)
        
        return unique_by_content
    
    def _dedupe_by_url(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove articles with duplicate URLs, keeping preferred version."""
        url_to_articles: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        for article in articles:
            url = self._normalize_url(article.get('url', ''))
            if url:
                url_to_articles[url].append(article)
        
        result = []
        for url, dupes in url_to_articles.items():
            if len(dupes) == 1:
                result.append(dupes[0])
            else:
                # Multiple articles with same URL - pick best one
                best = self._pick_best_article(dupes)
                result.append(best)
                self.stats['url_duplicates'] += len(dupes) - 1
        
        return result
    
    def _dedupe_by_content(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove articles with similar content using shingling."""
        if len(articles) < 2:
            return articles
        
        # Group by source and language to reduce comparisons
        groups = defaultdict(list)
        for i, article in enumerate(articles):
            key = (article.get('source', ''), article.get('language', ''))
            groups[key].append((i, article))
        
        duplicates: Set[int] = set()
        
        for key, group_articles in groups.items():
            # Compare within each group
            for i in range(len(group_articles)):
                if group_articles[i][0] in duplicates:
                    continue
                    
                for j in range(i + 1, len(group_articles)):
                    if group_articles[j][0] in duplicates:
                        continue
                    
                    idx_i, art_i = group_articles[i]
                    idx_j, art_j = group_articles[j]
                    
                    if self._is_similar(art_i, art_j):
                        # Mark the less preferred one as duplicate
                        worse = self._pick_worse_article(art_i, art_j)
                        if worse == art_i:
                            duplicates.add(idx_i)
                        else:
                            duplicates.add(idx_j)
                        self.stats['content_duplicates'] += 1
        
        # Return non-duplicate articles
        return [art for i, art in enumerate(articles) if i not in duplicates]
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        if not url:
            return ""
        
        # Remove protocol
        url = re.sub(r'^https?://', '', url.lower())
        
        # Remove www.
        url = re.sub(r'^www\.', '', url)
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Remove common tracking parameters
        url = re.sub(r'\?.*$', '', url)
        
        return url
    
    def _get_shingles(self, text: str, k: int = 3) -> Set[str]:
        """Get k-shingles (word n-grams) from text."""
        if not text:
            return set()
        
        # Normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        
        if len(words) < k:
            return {' '.join(words)}
        
        return {' '.join(words[i:i+k]) for i in range(len(words) - k + 1)}
    
    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _is_similar(self, art1: Dict[str, Any], art2: Dict[str, Any]) -> bool:
        """Check if two articles are similar based on content."""
        # First check title similarity (quick check)
        title1 = art1.get('title', '')
        title2 = art2.get('title', '')
        
        title_shingles1 = self._get_shingles(title1, k=2)
        title_shingles2 = self._get_shingles(title2, k=2)
        
        title_sim = self._jaccard_similarity(title_shingles1, title_shingles2)
        
        if title_sim < 0.5:
            # Titles too different, not duplicates
            return False
        
        # Check body similarity
        body1 = art1.get('body', '')
        body2 = art2.get('body', '')
        
        body_shingles1 = self._get_shingles(body1, k=3)
        body_shingles2 = self._get_shingles(body2, k=3)
        
        body_sim = self._jaccard_similarity(body_shingles1, body_shingles2)
        
        return body_sim >= self.similarity_threshold
    
    def _parse_crawl_date(self, article: Dict[str, Any]) -> Optional[datetime]:
        """Parse crawl_at timestamp."""
        crawled_at = article.get('crawled_at', '')
        if not crawled_at:
            return None
        
        try:
            # Handle ISO format with microseconds
            if '.' in crawled_at:
                return datetime.fromisoformat(crawled_at.replace('Z', '+00:00'))
            return datetime.fromisoformat(crawled_at)
        except (ValueError, TypeError):
            return None
    
    def _pick_best_article(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Pick the best article from duplicates."""
        if len(articles) == 1:
            return articles[0]
        
        if self.prefer_recent:
            # Sort by crawl date descending (most recent first)
            sorted_arts = sorted(
                articles,
                key=lambda a: self._parse_crawl_date(a) or datetime.min,
                reverse=True
            )
            return sorted_arts[0]
        else:
            # Pick the one with most tokens (most complete)
            return max(articles, key=lambda a: a.get('tokens', 0))
    
    def _pick_worse_article(self, art1: Dict[str, Any], art2: Dict[str, Any]) -> Dict[str, Any]:
        """Pick the worse article between two duplicates."""
        if self.prefer_recent:
            date1 = self._parse_crawl_date(art1)
            date2 = self._parse_crawl_date(art2)
            
            if date1 and date2:
                return art1 if date1 < date2 else art2
            elif date1:
                return art2  # Keep the one with a date
            elif date2:
                return art1
        
        # Fall back to token count
        tokens1 = art1.get('tokens', 0)
        tokens2 = art2.get('tokens', 0)
        
        return art1 if tokens1 < tokens2 else art2
    
    def get_stats(self) -> Dict[str, int]:
        """Return deduplication statistics."""
        return self.stats.copy()
