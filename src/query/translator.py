"""
Query translation between Bangla and English
Uses multiple translation methods with fallback
"""

import re
from typing import Optional, Dict
from googletrans import Translator

class QueryTranslator:
    """
    Handles translation between Bangla and English
    Uses Google Translate API with fallback mechanisms
    """
    
    def __init__(self):
        self.translator = Translator()
        
        # Common entity mappings (can be expanded)
        self.entity_map = {
            'en_to_bn': {
                'dhaka': 'ঢাকা',
                'bangladesh': 'বাংলাদেশ',
                'chittagong': 'চট্টগ্রাম',
                'khulna': 'খুলনা',
                'rajshahi': 'রাজশাহী',
                'sylhet': 'সিলেট',
                'new york': 'নিউইয়র্ক',
                'london': 'লন্ডন',
                'india': 'ভারত',
                'america': 'আমেরিকা',
                'united states': 'যুক্তরাষ্ট্র',
                'president': 'রাষ্ট্রপতি',
                'prime minister': 'প্রধানমন্ত্রী',
                'parliament': 'সংসদ',
                'election': 'নির্বাচন',
                'government': 'সরকার',
                'development': 'উন্নয়ন',
                'economy': 'অর্থনীতি',
                'education': 'শিক্ষা',
                'health': 'স্বাস্থ্য',
            },
            'bn_to_en': {
                'ঢাকা': 'dhaka',
                'বাংলাদেশ': 'bangladesh',
                'চট্টগ্রাম': 'chittagong',
                'খুলনা': 'khulna',
                'রাজশাহী': 'rajshahi',
                'সিলেট': 'sylhet',
                'নিউইয়র্ক': 'new york',
                'লন্ডন': 'london',
                'ভারত': 'india',
                'আমেরিকা': 'america',
                'যুক্তরাষ্ট্র': 'united states',
                'রাষ্ট্রপতি': 'president',
                'প্রধানমন্ত্রী': 'prime minister',
                'সংসদ': 'parliament',
                'নির্বাচন': 'election',
                'সরকার': 'government',
                'উন্নয়ন': 'development',
                'অর্থনীতি': 'economy',
                'শিক্ষা': 'education',
                'স্বাস্থ্য': 'health',
            }
        }
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text from source_lang to target_lang
        Supports: 'en' -> 'bn' and 'bn' -> 'en'
        """
        if not text or source_lang == target_lang:
            return text
        
        # Validate language codes
        if source_lang not in ['en', 'bn'] or target_lang not in ['en', 'bn']:
            raise ValueError(f"Unsupported language pair: {source_lang}->{target_lang}")
        
        # Try dictionary-based translation first (for common terms)
        dict_translated = self._dictionary_translate(text, source_lang, target_lang)
        if dict_translated and dict_translated != text:
            return dict_translated
        
        # Use Google Translate API
        try:
            # Map language codes for Google Translate
            lang_map = {'en': 'en', 'bn': 'bn'}
            
            translated = self.translator.translate(
                text, 
                src=lang_map[source_lang],
                dest=lang_map[target_lang]
            )
            return translated.text
        except Exception as e:
            print(f"Translation error: {e}")
            # Fallback: return original text or dictionary translation
            return dict_translated or text
    
    def _dictionary_translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Simple dictionary-based translation for common terms
        """
        if source_lang == 'en' and target_lang == 'bn':
            mapping = self.entity_map['en_to_bn']
            # Try to translate whole phrase first
            lower_text = text.lower()
            if lower_text in mapping:
                return mapping[lower_text]
            
            # Translate word by word
            words = text.split()
            translated_words = []
            for word in words:
                lower_word = word.lower()
                if lower_word in mapping:
                    translated_words.append(mapping[lower_word])
                else:
                    translated_words.append(word)
            return ' '.join(translated_words)
        
        elif source_lang == 'bn' and target_lang == 'en':
            mapping = self.entity_map['bn_to_en']
            # Direct mapping for Bangla phrases
            if text in mapping:
                return mapping[text]
            
            # For longer Bangla text, Google Translate is better
            return None
        
        return None
    
    def translate_query_for_search(self, query: str, source_lang: str) -> Dict:
        """
        Translate query for cross-lingual search
        Returns both original and translated versions
        """
        target_lang = 'bn' if source_lang == 'en' else 'en'
        
        translated = self.translate(query, source_lang, target_lang)
        
        return {
            'original': query,
            'source_lang': source_lang,
            'translated': translated,
            'target_lang': target_lang,
            'search_queries': [query, translated]  # Both versions for search
        }
    
    def batch_translate(self, queries: list, source_lang: str, target_lang: str) -> list:
        """Translate multiple queries at once"""
        return [self.translate(q, source_lang, target_lang) for q in queries]