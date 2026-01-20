"""
Retrieval Module
================
This module provides various information retrieval methods for cross-lingual search.

Available Methods:
- BM25Search: Traditional keyword-based search using BM25 algorithm
- FuzzySearch: Fuzzy matching for handling typos and transliteration
- SemanticSearch: Embedding-based semantic search with cross-lingual support
- HybridSearch: Combined approach using all three methods

Example Usage:
    from src.retrieval import HybridSearch
    
    # Load your documents
    documents = [...]
    
    # Initialize search
    search = HybridSearch(documents)
    
    # Search
    results = search.search("your query", k=5)
"""

from .bm25 import BM25Search
from .fuzzy import FuzzySearch
from .semantic import SemanticSearch
from .hybrid import HybridSearch

__all__ = ['BM25Search', 'FuzzySearch', 'SemanticSearch', 'HybridSearch']
