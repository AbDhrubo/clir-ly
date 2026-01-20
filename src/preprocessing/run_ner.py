"""
Standalone NER processing script for Kaggle/Colab.

Usage:
    python run_ner.py --input data/processed/articles_all.jsonl --output data/processed/articles_with_ner.jsonl
    
On Kaggle:
    !python run_ner.py --input /kaggle/input/clir-articles/articles_all.jsonl --output articles_with_ner.jsonl --gpu
"""

import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def load_articles(filepath: str) -> List[Dict[str, Any]]:
    """Load articles from JSONL file."""
    articles = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                articles.append(json.loads(line))
    return articles


def save_articles(articles: List[Dict[str, Any]], filepath: str):
    """Save articles to JSONL file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for article in articles:
            f.write(json.dumps(article, ensure_ascii=False) + '\n')


def run_ner_pipeline(
    input_path: str,
    output_path: str,
    use_gpu: bool = True,
    batch_size: int = 1,
    en_model: str = "en_core_web_trf",
    bn_model: str = "sagorsarker/mbert-bengali-ner",
    bn_confidence: float = 0.5,
):
    """
    Run NER on all articles.
    
    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file
        use_gpu: Whether to use GPU
        batch_size: Batch size for processing (currently processes one at a time)
        en_model: spaCy model for English
        bn_model: HuggingFace model for Bangla
        bn_confidence: Confidence threshold for Bangla NER
    """
    from ner_extractor import NERProcessor
    
    start_time = datetime.now()
    
    # Load articles
    logger.info(f"Loading articles from {input_path}")
    articles = load_articles(input_path)
    logger.info(f"Loaded {len(articles)} articles")
    
    # Separate by language
    en_articles = [a for a in articles if a.get('language') == 'en']
    bn_articles = [a for a in articles if a.get('language') == 'bn']
    
    logger.info(f"English articles: {len(en_articles)}")
    logger.info(f"Bangla articles: {len(bn_articles)}")
    
    # Initialize processor
    logger.info("Initializing NER processor...")
    processor = NERProcessor(
        use_gpu=use_gpu,
        en_model=en_model,
        bn_model=bn_model,
        bn_confidence=bn_confidence
    )
    
    processed_articles = []
    total_entities = 0
    
    # Process English articles
    logger.info("\n" + "="*50)
    logger.info("Processing English articles...")
    logger.info("="*50)
    
    for article in tqdm(en_articles, desc="English NER"):
        try:
            processed = processor.process_article(article)
            total_entities += len(processed.get('named_entities', []))
            processed_articles.append(processed)
        except Exception as e:
            logger.error(f"Error processing article {article.get('url', 'unknown')}: {e}")
            article['named_entities'] = []
            processed_articles.append(article)
    
    # Process Bangla articles
    logger.info("\n" + "="*50)
    logger.info("Processing Bangla articles...")
    logger.info("="*50)
    
    for article in tqdm(bn_articles, desc="Bangla NER"):
        try:
            processed = processor.process_article(article)
            total_entities += len(processed.get('named_entities', []))
            processed_articles.append(processed)
        except Exception as e:
            logger.error(f"Error processing article {article.get('url', 'unknown')}: {e}")
            article['named_entities'] = []
            processed_articles.append(article)
    
    # Save results
    logger.info(f"\nSaving {len(processed_articles)} articles to {output_path}")
    save_articles(processed_articles, output_path)
    
    # Statistics
    elapsed = (datetime.now() - start_time).total_seconds()
    avg_entities = total_entities / len(processed_articles) if processed_articles else 0
    
    logger.info("\n" + "="*50)
    logger.info("NER PROCESSING COMPLETE")
    logger.info("="*50)
    logger.info(f"Total articles: {len(processed_articles)}")
    logger.info(f"Total entities extracted: {total_entities}")
    logger.info(f"Average entities per article: {avg_entities:.1f}")
    logger.info(f"Processing time: {elapsed:.1f} seconds")
    logger.info(f"Speed: {len(processed_articles) / elapsed:.1f} articles/second")
    
    return {
        'articles_processed': len(processed_articles),
        'total_entities': total_entities,
        'avg_entities': avg_entities,
        'elapsed_seconds': elapsed
    }


def main():
    parser = argparse.ArgumentParser(description="Run NER on articles")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file")
    parser.add_argument("--output", "-o", required=True, help="Output JSONL file")
    parser.add_argument("--gpu", action="store_true", help="Use GPU acceleration")
    parser.add_argument("--en-model", default="en_core_web_trf", 
                       help="spaCy model for English")
    parser.add_argument("--bn-model", default="sagorsarker/mbert-bengali-ner",
                       help="HuggingFace model for Bangla")
    parser.add_argument("--bn-confidence", type=float, default=0.5,
                       help="Confidence threshold for Bangla NER (0.0-1.0)")
    
    args = parser.parse_args()
    
    results = run_ner_pipeline(
        input_path=args.input,
        output_path=args.output,
        use_gpu=args.gpu,
        en_model=args.en_model,
        bn_model=args.bn_model,
        bn_confidence=args.bn_confidence
    )
    
    print(f"\nDone! Extracted {results['total_entities']} entities from {results['articles_processed']} articles.")


if __name__ == "__main__":
    main()
