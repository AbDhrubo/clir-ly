"""
Main query processing pipeline orchestrator
Combines all components for end-to-end query processing
"""

from typing import Dict, List
import re
from .detector import HybridLanguageDetector
from .translator import QueryTranslator
from .expander import QueryExpander
from .ne_mapper import NERMapper

class QueryProcessingPipeline:
    """
    Complete query processing pipeline for cross-lingual search
    """
    
    def __init__(self, 
                 use_translation: bool = True,
                 use_expansion: bool = True,
                 use_ner_mapping: bool = True):
        
        # Initialize components
        self.detector = HybridLanguageDetector()
        self.translator = QueryTranslator() if use_translation else None
        self.expander = QueryExpander() if use_expansion else None
        self.ner_mapper = NERMapper() if use_ner_mapping else None
        
        # Configuration
        self.use_translation = use_translation
        self.use_expansion = use_expansion
        self.use_ner_mapping = use_ner_mapping
    
    def normalize_query(self, query: str, lang: str) -> str:
        """
        Normalize query: lowercase, remove extra whitespace, etc.
        """
        if not query:
            return ""
        
        # Remove extra whitespace
        query = re.sub(r'\s+', ' ', query.strip())
        
        # Lowercase for English
        if lang == 'en':
            query = query.lower()
        
        # Remove excessive punctuation (optional)
        # query = re.sub(r'[^\w\s\u0980-\u09FF]', ' ', query)
        
        return query
    
    def process(self, raw_query: str) -> Dict:
        """
        Main processing pipeline
        """
        if not raw_query or not raw_query.strip():
            return self._empty_response()
        
        # Step 1: Language Detection
        lang_result = self.detector.detect_with_details(raw_query)
        detected_lang = lang_result['language']
        
        # If language detection failed, default to English
        if detected_lang == 'unknown':
            detected_lang = 'en'
            lang_result['language'] = 'en'
            lang_result['is_english'] = True
        
        # Step 2: Normalization
        normalized_query = self.normalize_query(raw_query, detected_lang)
        
        # Step 3: Initialize results structure
        result = {
            'original_query': raw_query,
            'detected_language': detected_lang,
            'language_confidence': lang_result['confidence'],
            'normalized_query': normalized_query,
            'translation': None,
            'expansion': None,
            'ner_mapping': None,
            'final_search_queries': [normalized_query]
        }
        
        # Step 4: Query Translation (if enabled)
        if self.use_translation and self.translator:
            translation_result = self.translator.translate_query_for_search(
                normalized_query, 
                detected_lang
            )
            result['translation'] = translation_result
            result['final_search_queries'].append(translation_result['translated'])
        
        # Step 5: Query Expansion (if enabled)
        if self.use_expansion and self.expander:
            expansion_result = self.expander.expand_for_search(
                normalized_query, 
                detected_lang
            )
            result['expansion'] = expansion_result
            
            # Add expanded queries (limit to first 5 to avoid too many)
            expanded = expansion_result['expanded_queries'][:5]
            result['final_search_queries'].extend(expanded)
            
            # Also expand translated query if available
            if result['translation']:
                translated_expansion = self.expander.expand_for_search(
                    result['translation']['translated'],
                    result['translation']['target_lang']
                )
                result['translation']['expansion'] = translated_expansion
                result['final_search_queries'].extend(
                    translated_expansion['expanded_queries'][:3]
                )
        
        # Step 6: Named Entity Mapping (if enabled)
        if self.use_ner_mapping and self.ner_mapper:
            target_lang = 'bn' if detected_lang == 'en' else 'en'
            ner_result = self.ner_mapper.map_query_entities(
                normalized_query, 
                detected_lang, 
                target_lang
            )
            result['ner_mapping'] = ner_result
            
            # Add entity-mapped queries
            result['final_search_queries'].extend(ner_result['mapped_queries'])
        
        # Step 7: Deduplicate and clean final search queries
        unique_queries = []
        seen = set()
        for query in result['final_search_queries']:
            if query and query.strip() and query not in seen:
                seen.add(query)
                unique_queries.append(query)
        
        result['final_search_queries'] = unique_queries
        result['total_search_variations'] = len(unique_queries)
        
        return result
    
    def _empty_response(self) -> Dict:
        """Return empty response structure"""
        return {
            'original_query': '',
            'detected_language': 'unknown',
            'language_confidence': 0.0,
            'normalized_query': '',
            'translation': None,
            'expansion': None,
            'ner_mapping': None,
            'final_search_queries': [],
            'total_search_variations': 0
        }
    
    def batch_process(self, queries: List[str]) -> List[Dict]:
        """Process multiple queries"""
        return [self.process(query) for query in queries]
    
    def get_config(self) -> Dict:
        """Get current pipeline configuration"""
        return {
            'use_translation': self.use_translation,
            'use_expansion': self.use_expansion,
            'use_ner_mapping': self.use_ner_mapping
        }