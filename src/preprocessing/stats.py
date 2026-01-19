"""
Data statistics and quality metrics for preprocessing.

Tracks:
- Article counts by source/language
- Token distribution
- Quality metrics before/after cleaning
"""

import json
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataStats:
    """Track and report data quality statistics."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all statistics."""
        self.stats = {
            'before': self._empty_stats(),
            'after': self._empty_stats(),
            'cleaning': {
                'articles_processed': 0,
                'articles_removed': 0,
                'duplicates_removed': 0,
                'short_articles_removed': 0,
                'empty_articles_removed': 0,
            }
        }
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Create empty stats structure."""
        return {
            'total_articles': 0,
            'by_language': defaultdict(int),
            'by_source': defaultdict(int),
            'by_source_language': defaultdict(int),
            'token_stats': {
                'total': 0,
                'min': float('inf'),
                'max': 0,
                'avg': 0.0,
            },
            'date_range': {
                'earliest': None,
                'latest': None,
            }
        }
    
    def compute_stats(self, articles: List[Dict[str, Any]], phase: str = 'before') -> Dict[str, Any]:
        """
        Compute statistics for a list of articles.
        
        Args:
            articles: List of article dictionaries
            phase: 'before' or 'after' cleaning
            
        Returns:
            Statistics dictionary
        """
        stats = self._empty_stats()
        stats['total_articles'] = len(articles)
        
        token_counts = []
        dates = []
        
        for article in articles:
            language = article.get('language', 'unknown')
            source = article.get('source', 'unknown')
            tokens = article.get('tokens', 0)
            date = article.get('date')
            
            stats['by_language'][language] += 1
            stats['by_source'][source] += 1
            stats['by_source_language'][f"{source}_{language}"] += 1
            
            token_counts.append(tokens)
            
            if date:
                dates.append(date)
        
        # Token statistics
        if token_counts:
            stats['token_stats']['total'] = sum(token_counts)
            stats['token_stats']['min'] = min(token_counts)
            stats['token_stats']['max'] = max(token_counts)
            stats['token_stats']['avg'] = sum(token_counts) / len(token_counts)
        
        # Date range
        if dates:
            sorted_dates = sorted(dates)
            stats['date_range']['earliest'] = sorted_dates[0]
            stats['date_range']['latest'] = sorted_dates[-1]
        
        # Convert defaultdicts to regular dicts for JSON serialization
        stats['by_language'] = dict(stats['by_language'])
        stats['by_source'] = dict(stats['by_source'])
        stats['by_source_language'] = dict(stats['by_source_language'])
        
        self.stats[phase] = stats
        return stats
    
    def record_removal(self, reason: str, count: int = 1):
        """Record article removal."""
        if reason == 'duplicate':
            self.stats['cleaning']['duplicates_removed'] += count
        elif reason == 'short':
            self.stats['cleaning']['short_articles_removed'] += count
        elif reason == 'empty':
            self.stats['cleaning']['empty_articles_removed'] += count
        self.stats['cleaning']['articles_removed'] += count
    
    def record_processed(self, count: int = 1):
        """Record processed articles."""
        self.stats['cleaning']['articles_processed'] += count
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """Calculate quality improvement metrics."""
        before = self.stats['before']
        after = self.stats['after']
        
        metrics = {
            'articles': {
                'before': before['total_articles'],
                'after': after['total_articles'],
                'removed': before['total_articles'] - after['total_articles'],
                'retention_rate': (after['total_articles'] / before['total_articles'] * 100) 
                                  if before['total_articles'] > 0 else 0,
            },
            'tokens': {
                'before_total': before['token_stats']['total'],
                'after_total': after['token_stats']['total'],
                'before_avg': before['token_stats']['avg'],
                'after_avg': after['token_stats']['avg'],
            },
            'cleaning_details': self.stats['cleaning'],
        }
        
        return metrics
    
    def get_summary(self) -> str:
        """Get human-readable summary of statistics."""
        metrics = self.get_quality_metrics()
        
        lines = [
            "=" * 60,
            "DATA CLEANING SUMMARY",
            "=" * 60,
            "",
            "ARTICLE COUNTS:",
            f"  Before cleaning: {metrics['articles']['before']:,}",
            f"  After cleaning:  {metrics['articles']['after']:,}",
            f"  Removed:         {metrics['articles']['removed']:,}",
            f"  Retention rate:  {metrics['articles']['retention_rate']:.1f}%",
            "",
            "REMOVAL BREAKDOWN:",
            f"  Duplicates:      {self.stats['cleaning']['duplicates_removed']:,}",
            f"  Short articles:  {self.stats['cleaning']['short_articles_removed']:,}",
            f"  Empty articles:  {self.stats['cleaning']['empty_articles_removed']:,}",
            "",
            "TOKEN STATISTICS:",
            f"  Before - Total: {metrics['tokens']['before_total']:,}, Avg: {metrics['tokens']['before_avg']:.1f}",
            f"  After  - Total: {metrics['tokens']['after_total']:,}, Avg: {metrics['tokens']['after_avg']:.1f}",
            "",
        ]
        
        # By language
        lines.append("BY LANGUAGE (after cleaning):")
        for lang, count in sorted(self.stats['after']['by_language'].items()):
            lines.append(f"  {lang}: {count:,}")
        
        lines.append("")
        lines.append("BY SOURCE (after cleaning):")
        for source, count in sorted(self.stats['after']['by_source'].items()):
            lines.append(f"  {source}: {count:,}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all stats as dictionary."""
        return {
            'before': self.stats['before'],
            'after': self.stats['after'],
            'cleaning': self.stats['cleaning'],
            'metrics': self.get_quality_metrics(),
            'generated_at': datetime.now().isoformat(),
        }
    
    def save_report(self, filepath: str):
        """Save statistics report to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Saved cleaning report to {filepath}")
