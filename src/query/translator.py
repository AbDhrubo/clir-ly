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


def translate_query(text: str, source_lang: str, target_lang: str) -> str:
    """
    Translate query from source to target language.
    
    Args:
        text: Query text
        source_lang: 'en' or 'bn'
        target_lang: 'en' or 'bn'
        
    Returns:
        Translated text (or original if translation fails)
    """
    if source_lang == target_lang:
        return text
    
    if source_lang == 'bn' and target_lang == 'en':
        return translate_bn_to_en(text)
    elif source_lang == 'en' and target_lang == 'bn':
        return translate_en_to_bn(text)
    else:
        return text
