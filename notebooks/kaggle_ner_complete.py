"""
CLIR-ly NER Processing Script for Kaggle
=========================================

A self-contained script for Named Entity Recognition on bilingual (English/Bangla) articles.

Usage on Kaggle:
1. Create a new notebook
2. Add your articles_all.jsonl as a dataset
3. Copy this entire script into a code cell
4. Run it!

Models:
- English: spaCy en_core_web_trf (all entity types)
- Bangla: sagorsarker/mbert-bengali-ner (PERSON, ORG, LOC)
"""

# ============================================================================
# SETUP - Run this cell first!
# ============================================================================

import subprocess
import sys

def install_dependencies():
    """Install required packages."""
    print("Installing dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", 
                    "spacy", "transformers", "torch", "tqdm"])
    subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_trf", "-q"])
    print("Dependencies installed!")

# Uncomment the line below on first run:
# install_dependencies()

# ============================================================================
# NER EXTRACTOR CLASSES
# ============================================================================

import json
import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class BaseNERExtractor(ABC):
    """Abstract base class for NER extractors."""
    
    @abstractmethod
    def extract(self, text: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        pass


class EnglishNERExtractor(BaseNERExtractor):
    """
    English NER using spaCy transformer model.
    
    Entity types: PERSON, NORP, FAC, ORG, GPE, LOC, PRODUCT, EVENT, 
                  WORK_OF_ART, LAW, LANGUAGE, DATE, TIME, PERCENT, 
                  MONEY, QUANTITY, ORDINAL, CARDINAL
    """
    
    def __init__(self, model_name: str = "en_core_web_trf", use_gpu: bool = True):
        import spacy
        
        if use_gpu:
            try:
                spacy.require_gpu()
                logger.info("GPU enabled for spaCy")
            except Exception:
                logger.info("GPU not available for spaCy, using CPU")
        
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except OSError:
            logger.warning(f"Model {model_name} not found, downloading...")
            subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
            self.nlp = spacy.load(model_name)
        
        self.model_name = model_name
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []
        
        # Truncate very long texts
        max_chars = 100000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        doc = self.nlp(text)
        
        entities = []
        seen = set()
        
        for ent in doc.ents:
            key = (ent.text.strip(), ent.label_)
            if key in seen:
                continue
            seen.add(key)
            
            entities.append({
                "text": ent.text.strip(),
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            })
        
        return entities
    
    def get_model_name(self) -> str:
        return self.model_name


class BanglaNERExtractor(BaseNERExtractor):
    """
    Bangla NER using multilingual BERT fine-tuned on WikiAnn.
    Entity types: PERSON, ORG, LOC
    """
    
    def __init__(self, 
                 model_name: str = "sagorsarker/mbert-bengali-ner",
                 use_gpu: bool = True,
                 min_confidence: float = 0.5):
        from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        import torch
        
        self.model_name = model_name
        self.min_confidence = min_confidence
        
        if use_gpu and torch.cuda.is_available():
            self.device = 0
            logger.info("GPU enabled for Bangla NER")
        else:
            self.device = -1
            logger.info("Using CPU for Bangla NER")
        
        logger.info(f"Loading Bangla NER model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device,
            aggregation_strategy="simple"
        )
        logger.info("Bangla NER model loaded successfully")
    
    def extract(self, text: str, min_confidence: Optional[float] = None) -> List[Dict[str, Any]]:
        if not text or not text.strip():
            return []
        
        threshold = min_confidence if min_confidence is not None else self.min_confidence
        
        max_chars = 50000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        try:
            results = self.ner_pipeline(text)
        except Exception as e:
            logger.warning(f"NER extraction failed: {e}")
            return []
        
        entities = []
        seen = set()
        
        for ent in results:
            score = ent.get("score", 1.0)
            if score < threshold:
                continue
            
            raw_label = ent.get("entity_group", ent.get("entity", ""))
            label = self._map_label(raw_label)
            if label is None:
                continue
            
            text_val = ent.get("word", "").strip().replace("##", "").strip()
            if not text_val:
                continue
            
            key = (text_val, label)
            if key in seen:
                continue
            seen.add(key)
            
            entities.append({
                "text": text_val,
                "label": label,
                "start": ent.get("start", 0),
                "end": ent.get("end", 0),
                "confidence": round(score, 3),
            })
        
        return entities
    
    def _map_label(self, raw_label: str) -> Optional[str]:
        label_upper = raw_label.upper()
        if "PER" in label_upper:
            return "PERSON"
        elif "ORG" in label_upper:
            return "ORG"
        elif "LOC" in label_upper:
            return "LOC"
        return None
    
    def get_model_name(self) -> str:
        return self.model_name


class NERProcessor:
    """Main NER processor for both English and Bangla."""
    
    def __init__(self, 
                 use_gpu: bool = True,
                 en_model: str = "en_core_web_trf",
                 bn_model: str = "sagorsarker/mbert-bengali-ner",
                 bn_confidence: float = 0.5):
        self.use_gpu = use_gpu
        self.en_model_name = en_model
        self.bn_model_name = bn_model
        self.bn_confidence = bn_confidence
        self._en_extractor = None
        self._bn_extractor = None
    
    @property
    def en_extractor(self) -> EnglishNERExtractor:
        if self._en_extractor is None:
            self._en_extractor = EnglishNERExtractor(
                model_name=self.en_model_name,
                use_gpu=self.use_gpu
            )
        return self._en_extractor
    
    @property
    def bn_extractor(self) -> BanglaNERExtractor:
        if self._bn_extractor is None:
            self._bn_extractor = BanglaNERExtractor(
                model_name=self.bn_model_name,
                use_gpu=self.use_gpu,
                min_confidence=self.bn_confidence
            )
        return self._bn_extractor
    
    def extract_entities(self, text: str, language: str) -> List[Dict[str, Any]]:
        if language == "en":
            return self.en_extractor.extract(text)
        elif language == "bn":
            return self.bn_extractor.extract(text)
        else:
            logger.warning(f"Unknown language: {language}")
            return []
    
    def process_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        text = article.get("body", "")
        language = article.get("language", "en")
        entities = self.extract_entities(text, language)
        article_copy = article.copy()
        article_copy["named_entities"] = entities
        return article_copy


# ============================================================================
# PIPELINE FUNCTIONS
# ============================================================================

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
    bn_confidence: float = 0.5,
):
    """
    Run NER on all articles.
    
    Args:
        input_path: Path to input JSONL file
        output_path: Path to output JSONL file
        use_gpu: Whether to use GPU
        bn_confidence: Confidence threshold for Bangla NER
    """
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
    processor = NERProcessor(use_gpu=use_gpu, bn_confidence=bn_confidence)
    
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
            logger.error(f"Error: {e}")
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
            logger.error(f"Error: {e}")
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


# ============================================================================
# MAIN EXECUTION - THIS RUNS AUTOMATICALLY!
# ============================================================================

# ========================================
# CONFIGURATION - EDIT THESE PATHS!
# ========================================

INPUT_PATH = "/kaggle/input/clir-articles/articles_all.jsonl"  # Your input file
OUTPUT_PATH = "/kaggle/working/articles_with_ner.jsonl"        # Output file

print("="*60)
print("CLIR-ly NER PIPELINE")
print("="*60)
print(f"Input:  {INPUT_PATH}")
print(f"Output: {OUTPUT_PATH}")
print("="*60)

# Check if input file exists
import os
if not os.path.exists(INPUT_PATH):
    print(f"\n❌ ERROR: Input file not found: {INPUT_PATH}")
    print("\nAvailable files in /kaggle/input:")
    for root, dirs, files in os.walk("/kaggle/input"):
        for f in files[:10]:  # Show first 10 files
            print(f"  {os.path.join(root, f)}")
    print("\n👆 Please update INPUT_PATH with the correct path!")
else:
    print(f"\n✅ Found input file: {INPUT_PATH}")
    
    # Run the pipeline
    results = run_ner_pipeline(
        input_path=INPUT_PATH,
        output_path=OUTPUT_PATH,
        use_gpu=True,
        bn_confidence=0.5
    )
    
    print(f"\n✅ Done! Extracted {results['total_entities']} entities from {results['articles_processed']} articles.")
    print(f"📁 Output saved to: {OUTPUT_PATH}")
    
    # Download link for Kaggle
    try:
        from IPython.display import FileLink
        display(FileLink(OUTPUT_PATH))
    except:
        pass
