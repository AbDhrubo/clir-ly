"""
Language detection for Bangla and English queries
With fallback options when fasttext is not available
"""

import re
import os
import urllib.request
from typing import Dict, Optional, Tuple

class UnicodeDetector:
    """Fast Unicode-based language detection"""
    
    @staticmethod
    def detect(text: str, min_ratio: float = 0.3) -> Tuple[Optional[str], float]:
        """
        Detect language using Unicode character ranges
        Returns: (language_code, confidence)
        """
        if not text or len(text.strip()) < 2:
            return None, 0.0
        
        # Remove whitespace and punctuation for analysis
        clean_text = re.sub(r'[\s\.,!?;:\"\']+', '', text)
        if not clean_text:
            return None, 0.0
        
        # Count characters by script
        bangla_count = len(re.findall(r'[\u0980-\u09FF]', clean_text))
        english_count = len(re.findall(r'[a-zA-Z]', clean_text))
        total_count = len(clean_text)
        
        if total_count == 0:
            return None, 0.0
        
        bangla_ratio = bangla_count / total_count
        english_ratio = english_count / total_count
        
        # Determine language
        if bangla_ratio > min_ratio:
            return 'bn', bangla_ratio
        elif english_ratio > 0.7:
            return 'en', english_ratio
        else:
            # Mixed or uncertain
            if bangla_ratio > english_ratio and bangla_ratio > 0.1:
                return 'bn', bangla_ratio
            elif english_ratio > bangla_ratio and english_ratio > 0.1:
                return 'en', english_ratio
        
        return None, max(bangla_ratio, english_ratio)


class LangDetectDetector:
    """Language detection using langdetect library"""
    
    def __init__(self):
        try:
            from langdetect import detect, detect_langs, DetectorFactory
            from langdetect.lang_detect_exception import LangDetectException
            
            # For consistent results
            DetectorFactory.seed = 0
            
            self.detect_func = detect
            self.detect_langs_func = detect_langs
            self.LangDetectException = LangDetectException
            self.available = True
        except ImportError:
            self.available = False
    
    def detect(self, text: str) -> Tuple[Optional[str], float]:
        """
        Detect language using langdetect
        Returns: (language_code, confidence)
        """
        if not self.available or not text or len(text.strip()) < 2:
            return None, 0.0
        
        try:
            # Get language probabilities
            languages = self.detect_langs_func(text)
            
            # Find Bangla and English probabilities
            bn_prob = 0.0
            en_prob = 0.0
            
            for lang in languages:
                if lang.lang == 'bn':
                    bn_prob = lang.prob
                elif lang.lang == 'en':
                    en_prob = lang.prob
            
            # Determine language
            if bn_prob >= en_prob and bn_prob > 0.3:
                return 'bn', bn_prob
            elif en_prob >= bn_prob and en_prob > 0.3:
                return 'en', en_prob
            else:
                return None, max(bn_prob, en_prob)
                
        except self.LangDetectException:
            return None, 0.0


class TextBlobDetector:
    """Language detection using TextBlob"""
    
    def __init__(self):
        try:
            from textblob import TextBlob
            self.TextBlob = TextBlob
            self.available = True
        except ImportError:
            self.available = False
    
    def detect(self, text: str) -> Tuple[Optional[str], float]:
        """
        Detect language using TextBlob
        Returns: (language_code, confidence)
        """
        if not self.available or not text or len(text.strip()) < 2:
            return None, 0.0
        
        try:
            blob = self.TextBlob(text)
            # TextBlob doesn't directly give language detection
            # We'll use a simple heuristic instead
            return None, 0.5  # Placeholder
        except:
            return None, 0.0


class HybridLanguageDetector:
    """
    Main language detector combining multiple methods
    Uses Unicode detection as primary, falls back to other methods
    """
    
    def __init__(self, use_langdetect: bool = True, use_textblob: bool = False):
        self.unicode_detector = UnicodeDetector()
        self.langdetect_detector = None
        self.textblob_detector = None
        
        if use_langdetect:
            self.langdetect_detector = LangDetectDetector()
        
        if use_textblob:
            self.textblob_detector = TextBlobDetector()
    
    def detect(self, text: str) -> str:
        """
        Detect language of input text
        Returns: 'bn' (Bangla), 'en' (English), or 'unknown'
        """
        if not text or len(text.strip()) < 2:
            return 'unknown'
        
        # First try Unicode detection (fast and reliable for script distinction)
        lang, confidence = self.unicode_detector.detect(text)
        
        # If Unicode detection is confident (>0.7), return result
        if lang and confidence > 0.7:
            return lang
        
        # If Unicode detection gave some result with medium confidence
        if lang and confidence > 0.3:
            # Verify with langdetect if available
            if self.langdetect_detector and self.langdetect_detector.available:
                ld_lang, ld_conf = self.langdetect_detector.detect(text)
                if ld_lang == lang:
                    return lang
                elif ld_conf > 0.8:
                    return ld_lang
            return lang
        
        # Try langdetect if Unicode detection was uncertain
        if self.langdetect_detector and self.langdetect_detector.available:
            ld_lang, ld_conf = self.langdetect_detector.detect(text)
            if ld_lang and ld_conf > 0.5:
                return ld_lang
        
        # If still unknown, use character composition
        if len(text) > 0:
            bangla_chars = len(re.findall(r'[\u0980-\u09FF]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            
            if bangla_chars > english_chars * 2:  # Significantly more Bangla chars
                return 'bn'
            elif english_chars > bangla_chars * 2:  # Significantly more English chars
                return 'en'
            elif bangla_chars > 0:
                return 'bn'  # Default to Bangla if any Bangla characters
            elif english_chars > 0:
                return 'en'  # Default to English if any English characters
        
        return 'unknown'
    
    def detect_with_details(self, text: str) -> Dict:
        """
        Return detailed language detection results
        """
        result = {
            'language': 'unknown',
            'confidence': 0.0,
            'is_bangla': False,
            'is_english': False,
            'method': 'none',
            'bangla_chars': 0,
            'english_chars': 0,
            'total_chars': 0
        }
        
        if not text or len(text.strip()) < 2:
            return result
        
        # Count characters
        result['bangla_chars'] = len(re.findall(r'[\u0980-\u09FF]', text))
        result['english_chars'] = len(re.findall(r'[a-zA-Z]', text))
        result['total_chars'] = len(text)
        
        # Unicode detection
        unicode_lang, unicode_conf = self.unicode_detector.detect(text)
        
        if unicode_lang and unicode_conf > 0.7:
            result['language'] = unicode_lang
            result['confidence'] = unicode_conf
            result['is_bangla'] = (unicode_lang == 'bn')
            result['is_english'] = (unicode_lang == 'en')
            result['method'] = 'unicode'
            return result
        
        # LangDetect detection
        if self.langdetect_detector and self.langdetect_detector.available:
            ld_lang, ld_conf = self.langdetect_detector.detect(text)
            
            if ld_lang and ld_conf > 0.5:
                result['language'] = ld_lang
                result['confidence'] = ld_conf
                result['is_bangla'] = (ld_lang == 'bn')
                result['is_english'] = (ld_lang == 'en')
                result['method'] = 'langdetect'
                return result
        
        # Fallback: Use Unicode result if any
        if unicode_lang:
            result['language'] = unicode_lang
            result['confidence'] = unicode_conf
            result['is_bangla'] = (unicode_lang == 'bn')
            result['is_english'] = (unicode_lang == 'en')
            result['method'] = 'unicode_fallback'
        else:
            # Character count fallback
            if result['bangla_chars'] > result['english_chars']:
                result['language'] = 'bn'
                result['confidence'] = result['bangla_chars'] / max(result['total_chars'], 1)
                result['is_bangla'] = True
                result['method'] = 'char_count'
            elif result['english_chars'] > 0:
                result['language'] = 'en'
                result['confidence'] = result['english_chars'] / max(result['total_chars'], 1)
                result['is_english'] = True
                result['method'] = 'char_count'
        
        return result