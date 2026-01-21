"""
Query Processing Pipeline for Cross-Lingual Search
Modules for language detection, translation, expansion, and NER mapping
"""

from .detector import HybridLanguageDetector
from .translator import QueryTranslator
from .expander import QueryExpander
from .ne_mapper import NERMapper
from .pipeline import QueryProcessingPipeline

__version__ = "1.0.0"
__all__ = [
    'HybridLanguageDetector',
    'QueryTranslator',
    'QueryExpander', 
    'NERMapper',
    'QueryProcessingPipeline'
]