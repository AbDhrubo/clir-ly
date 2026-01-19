"""
Main data cleaning pipeline for CLIR-ly.

Orchestrates:
- Loading raw JSONL data
- Text cleaning and normalization
- Deduplication
- Validation and filtering
- Export to processed format
"""

import json
import glob
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .cleaner import TextCleaner, clean_article
from .deduplicator import Deduplicator
from .stats import DataStats

logger = logging.getLogger(__name__)


class CleaningPipeline:
    """Main data cleaning pipeline."""
    
    def __init__(self,
                 raw_dir: str = "data/raw",
                 output_dir: str = "data/processed",
                 min_tokens: int = 50,
                 similarity_threshold: float = 0.85):
        """
        Initialize cleaning pipeline.
        
        Args:
            raw_dir: Directory containing raw JSONL files
            output_dir: Directory for cleaned output
            min_tokens: Minimum token count for valid articles
            similarity_threshold: Threshold for content similarity dedup
        """
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.min_tokens = min_tokens
        
        # Initialize components
        self.cleaner = TextCleaner()
        self.deduplicator = Deduplicator(
            similarity_threshold=similarity_threshold,
            prefer_recent=True
        )
        self.stats = DataStats()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_raw_articles(self) -> List[Dict[str, Any]]:
        """Load all raw articles from JSONL files."""
        articles = []
        
        # Find all JSONL files
        pattern = str(self.raw_dir / "*_articles.jsonl")
        files = glob.glob(pattern)
        
        logger.info(f"Found {len(files)} raw article files")
        
        for filepath in files:
            count = 0
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        article = json.loads(line)
                        articles.append(article)
                        count += 1
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line in {filepath}: {e}")
            
            logger.info(f"Loaded {count} articles from {os.path.basename(filepath)}")
        
        return articles
    
    def validate_article(self, article: Dict[str, Any]) -> bool:
        """
        Validate if article meets quality criteria.
        
        Args:
            article: Article dictionary
            
        Returns:
            True if article is valid
        """
        # Check required fields
        if not article.get('url'):
            return False
        
        if not article.get('title'):
            self.stats.record_removal('empty')
            return False
        
        if not article.get('body'):
            self.stats.record_removal('empty')
            return False
        
        # Check minimum length
        tokens = article.get('tokens', 0)
        if tokens < self.min_tokens:
            self.stats.record_removal('short')
            return False
        
        return True
    
    def clean_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply text cleaning to all articles.
        
        Args:
            articles: List of raw articles
            
        Returns:
            List of cleaned articles
        """
        cleaned = []
        
        for article in articles:
            cleaned_article = clean_article(article, self.cleaner)
            
            if self.validate_article(cleaned_article):
                cleaned.append(cleaned_article)
                self.stats.record_processed()
        
        return cleaned
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete cleaning pipeline.
        
        Returns:
            Pipeline results with statistics
        """
        logger.info("=" * 60)
        logger.info("STARTING DATA CLEANING PIPELINE")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Step 1: Load raw data
        logger.info("\n[1/5] Loading raw articles...")
        raw_articles = self.load_raw_articles()
        self.stats.compute_stats(raw_articles, 'before')
        logger.info(f"Loaded {len(raw_articles)} raw articles")
        
        # Step 2: Clean articles
        logger.info("\n[2/5] Cleaning articles...")
        cleaned_articles = self.clean_articles(raw_articles)
        logger.info(f"After cleaning: {len(cleaned_articles)} articles")
        
        # Step 3: Deduplicate
        logger.info("\n[3/5] Removing duplicates...")
        deduped_articles = self.deduplicator.deduplicate(cleaned_articles)
        dedup_stats = self.deduplicator.get_stats()
        self.stats.record_removal('duplicate', dedup_stats['total_removed'])
        logger.info(f"After deduplication: {len(deduped_articles)} articles")
        
        # Step 4: Compute final stats
        logger.info("\n[4/5] Computing final statistics...")
        self.stats.compute_stats(deduped_articles, 'after')
        
        # Step 5: Save output
        logger.info("\n[5/5] Saving processed data...")
        self._save_articles(deduped_articles)
        self._save_report()
        
        # Log summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"\nPipeline completed in {elapsed:.1f} seconds")
        logger.info(self.stats.get_summary())
        
        return {
            'articles_count': len(deduped_articles),
            'stats': self.stats.to_dict(),
            'elapsed_seconds': elapsed,
        }
    
    def _save_articles(self, articles: List[Dict[str, Any]]):
        """Save cleaned articles to output files."""
        # Split by language
        en_articles = [a for a in articles if a.get('language') == 'en']
        bn_articles = [a for a in articles if a.get('language') == 'bn']
        
        # Save English articles
        en_path = self.output_dir / "articles_en.jsonl"
        self._save_jsonl(en_articles, en_path)
        logger.info(f"Saved {len(en_articles)} English articles to {en_path}")
        
        # Save Bangla articles
        bn_path = self.output_dir / "articles_bn.jsonl"
        self._save_jsonl(bn_articles, bn_path)
        logger.info(f"Saved {len(bn_articles)} Bangla articles to {bn_path}")
        
        # Save combined file
        all_path = self.output_dir / "articles_all.jsonl"
        self._save_jsonl(articles, all_path)
        logger.info(f"Saved {len(articles)} total articles to {all_path}")
    
    def _save_jsonl(self, articles: List[Dict[str, Any]], filepath: Path):
        """Save articles to JSONL file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(json.dumps(article, ensure_ascii=False) + '\n')
    
    def _save_report(self):
        """Save cleaning report."""
        report_path = self.output_dir / "cleaning_report.json"
        self.stats.save_report(str(report_path))


def run_pipeline(raw_dir: str = "data/raw",
                 output_dir: str = "data/processed",
                 min_tokens: int = 50) -> Dict[str, Any]:
    """
    Convenience function to run the cleaning pipeline.
    
    Args:
        raw_dir: Directory containing raw JSONL files
        output_dir: Directory for cleaned output
        min_tokens: Minimum token count for valid articles
        
    Returns:
        Pipeline results
    """
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    pipeline = CleaningPipeline(
        raw_dir=raw_dir,
        output_dir=output_dir,
        min_tokens=min_tokens
    )
    
    return pipeline.run()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run data cleaning pipeline")
    parser.add_argument("--raw-dir", default="data/raw", help="Raw data directory")
    parser.add_argument("--output-dir", default="data/processed", help="Output directory")
    parser.add_argument("--min-tokens", type=int, default=50, help="Minimum token count")
    
    args = parser.parse_args()
    
    results = run_pipeline(
        raw_dir=args.raw_dir,
        output_dir=args.output_dir,
        min_tokens=args.min_tokens
    )
    
    print(f"\nPipeline completed. Processed {results['articles_count']} articles.")
