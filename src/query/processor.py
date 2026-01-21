"""Main query processor - combines detection, normalization, translation."""

from .detector import detect_language, is_mixed_language
from .translator import translate_query
import logging

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Process queries for cross-lingual search."""
    
    def __init__(self):
        """Initialize processor."""
        self.lang_detected = None
        self.normalized = None
        self.original = None
        self.translated = None
    
    def process(self, query: str):
        """
        Process query through pipeline.
        
        Args:
            query: Raw user input
            
        Returns:
            dict with:
                - original: Original query
                - language: Detected language ('en' or 'bn')
                - normalized: Cleaned query
                - translated: Translated to other language
                - both_versions: List of [original, translated] for searching
        """
        self.original = query
        
        # Step 1: Normalize
        self.normalized = self._normalize(query)
        
        # Step 2: Detect language
        self.lang_detected = detect_language(self.normalized)
        
        # Step 3: Translate to other language
        target_lang = 'en' if self.lang_detected == 'bn' else 'bn'
        self.translated = translate_query(
            self.normalized, 
            self.lang_detected, 
            target_lang
        )
        
        # Return result
        result = {
            'original': self.original,
            'language': self.lang_detected,
            'normalized': self.normalized,
            'translated': self.translated,
            'both_versions': [self.normalized, self.translated],
            'is_mixed': is_mixed_language(self.normalized),
        }
        
        logger.info(f"Query processed: lang={self.lang_detected}, original='{self.original[:30]}...'")
        
        return result
    
    def _normalize(self, text: str) -> str:
        """Normalize query: lowercase, trim whitespace."""
        if not text:
            return ""
        
        # For Bangla: no lowercase needed (doesn't have it)
        # For English: lowercase
        text = text.strip()
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        return text


def process_query(query: str) -> dict:
    """Convenience function."""
    processor = QueryProcessor()
    return processor.process(query)
