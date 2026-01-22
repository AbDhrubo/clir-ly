"""Translate queries between English and Bangla using MarianMT."""

from transformers import MarianMTModel, MarianTokenizer
import logging

logger = logging.getLogger(__name__)

# Global models (loaded once)
_bn_to_en_model = None
_en_to_bn_model = None
_bn_to_en_tokenizer = None
_en_to_bn_tokenizer = None


def _load_bn_to_en():
    """Load Bangla to English translator."""
    global _bn_to_en_model, _bn_to_en_tokenizer
    if _bn_to_en_model is None:
        logger.info("Loading Bangla→English translation model...")
        model_name = "Helsinki-NLP/Opus-MT-bn-en"
        _bn_to_en_tokenizer = MarianTokenizer.from_pretrained(model_name)
        _bn_to_en_model = MarianMTModel.from_pretrained(model_name)
    return _bn_to_en_model, _bn_to_en_tokenizer


def _load_en_to_bn():
    """Load English to Bangla translator."""
    global _en_to_bn_model, _en_to_bn_tokenizer
    if _en_to_bn_model is None:
        logger.info("Loading English→Bangla translation model...")
        model_name = "shhossain/opus-mt-en-to-bn"
        _en_to_bn_tokenizer = MarianTokenizer.from_pretrained(model_name)
        _en_to_bn_model = MarianMTModel.from_pretrained(model_name)
    return _en_to_bn_model, _en_to_bn_tokenizer


def translate_bn_to_en(text: str) -> str:
    """Translate Bangla to English."""
    if not text or not text.strip():
        return ""
    
    try:
        model, tokenizer = _load_bn_to_en()
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
        outputs = model.generate(**inputs)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
    except Exception as e:
        logger.error(f"Translation error (bn→en): {e}")
        return text  # Return original if translation fails


def translate_en_to_bn(text: str) -> str:
    """Translate English to Bangla."""
    if not text or not text.strip():
        return ""
    
    try:
        model, tokenizer = _load_en_to_bn()
        inputs = tokenizer(text, return_tensors="pt", max_length=512, truncation=True)
        outputs = model.generate(**inputs)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
    except Exception as e:
        logger.error(f"Translation error (en→bn): {e}")
        return text  # Return original if translation fails


def translate_query(text: str, source_lang: str, target_lang: str, pinned_map: dict = None) -> str:
    """
    Translate query from source to target language.
    
    Args:
        text: Query text
        source_lang: 'en' or 'bn'
        target_lang: 'en' or 'bn'
        pinned_map: Optional dict of {phrase: translation} to preserve
        
    Returns:
        Translated text (or original if translation fails)
    """
    if not text:
        return ""
        
    if source_lang == target_lang:
        return text
    
    # If we have pinned translations, we try to preserve them
    # Simple strategy: replace phrase with placeholder, translate, then replace back
    # Safer strategy: if the whole query is a pinned entity, just return it
    if pinned_map:
        for phrase, translation in pinned_map.items():
            if text.lower().strip() == phrase.lower().strip():
                return translation

    # Perform translation
    if source_lang == 'bn' and target_lang == 'en':
        translated = translate_bn_to_en(text)
    elif source_lang == 'en' and target_lang == 'bn':
        translated = translate_en_to_bn(text)
    else:
        translated = text

    # After-translation pinning check
    # If pinned terms are missing from translation, we could append them
    # But for now, we'll keep it simple
    
    return translated
