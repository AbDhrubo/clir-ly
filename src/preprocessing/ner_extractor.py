"""
Named Entity Recognition extractor for English and Bangla articles.

Uses:
- English: spaCy transformer model (en_core_web_trf)
- Bangla: Multilingual BERT fine-tuned on WikiAnn (sagorsarker/mbert-bengali-ner)

Optimized for GPU (Kaggle/Colab compatible).
"""

import logging
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseNERExtractor(ABC):
    """Abstract base class for NER extractors."""
    
    @abstractmethod
    def extract(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model name/identifier."""
        pass


class EnglishNERExtractor(BaseNERExtractor):
    """
    English NER using spaCy transformer model.
    
    Entity types: PERSON, NORP, FAC, ORG, GPE, LOC, PRODUCT, EVENT, 
                  WORK_OF_ART, LAW, LANGUAGE, DATE, TIME, PERCENT, 
                  MONEY, QUANTITY, ORDINAL, CARDINAL
    """
    
    def __init__(self, model_name: str = "en_core_web_trf", use_gpu: bool = True):
        """
        Initialize English NER extractor.
        
        Args:
            model_name: spaCy model to use (trf = transformer, best accuracy)
            use_gpu: Whether to use GPU if available
        """
        import spacy
        
        # Enable GPU if requested and available
        if use_gpu:
            try:
                spacy.require_gpu()
                logger.info("GPU enabled for spaCy")
            except Exception:
                logger.info("GPU not available, using CPU")
        
        # Load model
        try:
            self.nlp = spacy.load(model_name)
            logger.info(f"Loaded spaCy model: {model_name}")
        except OSError:
            logger.warning(f"Model {model_name} not found, downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name], check=True)
            self.nlp = spacy.load(model_name)
        
        self.model_name = model_name
    
    def extract(self, text: str, min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """
        Extract named entities from English text.
        
        Args:
            text: Input text
            min_confidence: Minimum confidence threshold (spaCy doesn't provide 
                           confidence scores by default, so this is ignored)
        
        Returns:
            List of entity dictionaries
        """
        if not text or not text.strip():
            return []
        
        # Truncate very long texts to avoid memory issues
        max_chars = 100000
        if len(text) > max_chars:
            text = text[:max_chars]
        
        doc = self.nlp(text)
        
        entities = []
        seen = set()  # Deduplicate entities
        
        for ent in doc.ents:
            # Skip if already seen (same text and label)
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
    
    Entity types: PER (Person), ORG (Organization), LOC (Location)
    """
    
    # Label mapping from model output to standardized labels
    LABEL_MAP = {
        "B-PER": "PERSON",
        "I-PER": "PERSON",
        "B-ORG": "ORG",
        "I-ORG": "ORG",
        "B-LOC": "LOC",
        "I-LOC": "LOC",
        "O": None,
    }
    
    def __init__(self, 
                 model_name: str = "sagorsarker/mbert-bengali-ner",
                 use_gpu: bool = True,
                 min_confidence: float = 0.5):
        """
        Initialize Bangla NER extractor.
        
        Args:
            model_name: HuggingFace model identifier
            use_gpu: Whether to use GPU if available
            min_confidence: Minimum confidence threshold for entities
        """
        from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        import torch
        
        self.model_name = model_name
        self.min_confidence = min_confidence
        
        # Determine device
        if use_gpu and torch.cuda.is_available():
            self.device = 0  # First GPU
            logger.info("GPU enabled for Bangla NER")
        else:
            self.device = -1  # CPU
            logger.info("Using CPU for Bangla NER")
        
        # Load model and tokenizer
        logger.info(f"Loading Bangla NER model: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        # Create pipeline
        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device,
            aggregation_strategy="simple"  # Merge B-/I- tags
        )
        
        logger.info("Bangla NER model loaded successfully")
    
    def extract(self, text: str, min_confidence: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Extract named entities from Bangla text.
        
        Args:
            text: Input Bangla text
            min_confidence: Override default confidence threshold
        
        Returns:
            List of entity dictionaries
        """
        if not text or not text.strip():
            return []
        
        threshold = min_confidence if min_confidence is not None else self.min_confidence
        
        # Truncate very long texts
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
            # Filter by confidence
            score = ent.get("score", 1.0)
            if score < threshold:
                continue
            
            # Map label
            raw_label = ent.get("entity_group", ent.get("entity", ""))
            label = self._map_label(raw_label)
            if label is None:
                continue
            
            text_val = ent.get("word", "").strip()
            if not text_val:
                continue
            
            # Clean up subword tokens (remove ## prefix)
            text_val = text_val.replace("##", "").strip()
            
            # Deduplicate
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
        """Map model labels to standardized format."""
        # Handle aggregated labels (e.g., "PER", "ORG", "LOC")
        label_upper = raw_label.upper()
        
        if "PER" in label_upper:
            return "PERSON"
        elif "ORG" in label_upper:
            return "ORG"
        elif "LOC" in label_upper:
            return "LOC"
        
        return self.LABEL_MAP.get(raw_label)
    
    def get_model_name(self) -> str:
        return self.model_name


class NERProcessor:
    """
    Main NER processor that handles both English and Bangla.
    """
    
    def __init__(self, 
                 use_gpu: bool = True,
                 en_model: str = "en_core_web_trf",
                 bn_model: str = "sagorsarker/mbert-bengali-ner",
                 bn_confidence: float = 0.5):
        """
        Initialize NER processor for both languages.
        
        Args:
            use_gpu: Whether to use GPU
            en_model: spaCy model for English
            bn_model: HuggingFace model for Bangla
            bn_confidence: Confidence threshold for Bangla NER
        """
        self.use_gpu = use_gpu
        self.en_model_name = en_model
        self.bn_model_name = bn_model
        self.bn_confidence = bn_confidence
        
        # Lazy loading - models loaded on first use
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
        """
        Extract named entities based on language.
        
        Args:
            text: Input text
            language: "en" or "bn"
        
        Returns:
            List of entity dictionaries
        """
        if language == "en":
            return self.en_extractor.extract(text)
        elif language == "bn":
            return self.bn_extractor.extract(text)
        else:
            logger.warning(f"Unknown language: {language}")
            return []
    
    def process_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single article and add named_entities field.
        
        Args:
            article: Article dictionary with 'body' and 'language' fields
        
        Returns:
            Updated article with 'named_entities' populated
        """
        text = article.get("body", "")
        language = article.get("language", "en")
        
        entities = self.extract_entities(text, language)
        
        article_copy = article.copy()
        article_copy["named_entities"] = entities
        
        return article_copy
