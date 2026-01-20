"""
Preprocessing module for CLIR-ly data cleaning pipeline.
"""

from .cleaner import TextCleaner, clean_article
from .deduplicator import Deduplicator
from .pipeline import CleaningPipeline
from .stats import DataStats

# NER (lazy import to avoid loading heavy models)
def get_ner_processor(**kwargs):
    from .ner_extractor import NERProcessor
    return NERProcessor(**kwargs)

__all__ = [
    'TextCleaner',
    'clean_article', 
    'Deduplicator',
    'CleaningPipeline',
    'DataStats',
    'get_ner_processor',
]

