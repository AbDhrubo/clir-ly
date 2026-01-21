"""Detect if query is in English or Bangla."""

from langdetect import detect, LangDetectException


def detect_language(query: str) -> str:
    """
    Detect language of query.
    
    Args:
        query: Text to detect
        
    Returns:
        'en' for English, 'bn' for Bangla, 'unknown' if cannot detect
    """
    if not query or not query.strip():
        return 'unknown'
    
    try:
        lang = detect(query)
        
        # Map langdetect codes to our codes
        if lang == 'bn':
            return 'bn'
        elif lang in ['en']:
            return 'en'
        else:
            # Fallback: if mainly Bengali characters, it's Bangla
            bengali_chars = sum(1 for c in query if '\u0980' <= c <= '\u09FF')
            if bengali_chars > len(query) * 0.5:
                return 'bn'
            return 'en'  # Default to English
            
    except LangDetectException:
        # If detection fails, guess based on character set
        bengali_chars = sum(1 for c in query if '\u0980' <= c <= '\u09FF')
        if bengali_chars > len(query) * 0.3:
            return 'bn'
        return 'en'


def is_mixed_language(query: str) -> bool:
    """Check if query mixes Bangla and English."""
    bengali_chars = sum(1 for c in query if '\u0980' <= c <= '\u09FF')
    english_chars = sum(1 for c in query if c.isascii() and c.isalpha())
    
    total_chars = len(query)
    if total_chars == 0:
        return False
    
    bengali_ratio = bengali_chars / total_chars
    english_ratio = english_chars / total_chars
    
    # Mixed if both are present significantly
    return bengali_ratio > 0.1 and english_ratio > 0.1
