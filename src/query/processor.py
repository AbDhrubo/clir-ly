"""Main query processor - combines detection, normalization, translation."""

from .detector import detect_language, is_mixed_language
from .translator import translate_query
import logging
import json

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

logger = logging.getLogger(__name__)


class QueryProcessor:
    """Process queries for cross-lingual search."""
    
    def __init__(self, index_path: str = "data/processed/entity_index_linked.json"):
        """
        Initialize processor.
        
        Args:
            index_path: Path to the entity index JSON
        """
        self.lang_detected = None
        self.normalized = None
        self.original = None
        self.translated = None
        
        # Load entity index for EBQE
        self.entity_index = {}
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                self.entity_index = json.load(f)
            logger.info(f"Loaded {len(self.entity_index)} entities for EBQE.")
            
            # Create a lookup map for faster entity identification
            self.name_to_eid = {}
            for eid, data in self.entity_index.items():
                if data.get('canonical_en'):
                    self.name_to_eid[data['canonical_en'].lower().strip()] = eid
                if data.get('canonical_bn'):
                    self.name_to_eid[data['canonical_bn'].strip()] = eid
                for alias in data.get('aliases', []):
                    self.name_to_eid[alias.lower().strip()] = eid
                for alias in data.get('aliases_bn', []):
                    self.name_to_eid[alias.strip()] = eid
        except Exception as e:
            logger.error(f"Failed to load entity index: {e}")
        
        # Load Knowledge Graph for neighbor-based expansion
        self.graph = None
        if NETWORKX_AVAILABLE:
            try:
                graph_path = "data/processed/knowledge_graph/knowledge_graph.gexf"
                self.graph = nx.read_gexf(graph_path)
                logger.info(f"Loaded Knowledge Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")
            except Exception as e:
                logger.warning(f"Could not load Knowledge Graph: {e}")
    
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
        
        # Step 3: Translate to other language with "Pinned" entities
        target_lang = 'en' if self.lang_detected == 'bn' else 'bn'
        pinned_map = self.get_pinned_map(self.normalized, self.lang_detected, target_lang)
        
        self.translated = translate_query(
            self.normalized, 
            self.lang_detected, 
            target_lang,
            pinned_map=pinned_map
        )
        
        # Step 4: Expand query with entities (EBQE)
        self.expanded_en = self.expand_query(self.normalized if self.lang_detected == 'en' else self.translated, 'en')
        self.expanded_bn = self.expand_query(self.normalized if self.lang_detected == 'bn' else self.translated, 'bn')
        
        # Return result
        result = {
            'original': self.original,
            'language': self.lang_detected,
            'normalized': self.normalized,
            'translated': self.translated,
            'expanded_en': self.expanded_en,
            'expanded_bn': self.expanded_bn,
            'both_versions': [self.expanded_en, self.expanded_bn],
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

    def expand_query(self, query: str, lang: str) -> str:
        """
        Expand query using Knowledge Graph entities.
        
        Args:
            query: Normalized query string
            lang: Language of the query ('en' or 'bn')
            
        Returns:
            Expanded query string
        """
        if not query or not self.entity_index:
            return query
            
        expansion_terms = set(query.split())
        words = query.split()
        
        # Check for multi-word entities (sliding window)
        # We'll check windows of size 1 to 4
        for window_size in range(4, 0, -1):
            for i in range(len(words) - window_size + 1):
                phrase = " ".join(words[i:i+window_size])
                lookup_phrase = phrase.lower().strip() if lang == 'en' else phrase.strip()
                
                if lookup_phrase in self.name_to_eid:
                    eid = self.name_to_eid[lookup_phrase]
                    entity = self.entity_index[eid]
                    
                    # Add canonical names
                    if entity.get('canonical_en'):
                        expansion_terms.add(entity['canonical_en'])
                    if entity.get('canonical_bn'):
                        expansion_terms.add(entity['canonical_bn'])
                        
                    # Add top aliases (limit to 2 to avoid bloating)
                    aliases = entity.get('aliases', []) if lang == 'en' else entity.get('aliases_bn', [])
                    for alias in aliases[:2]:
                        expansion_terms.update(alias.split())
                    
                    # Graph-based expansion: add top neighbors
                    if self.graph and eid in self.graph:
                        neighbors = list(self.graph.neighbors(eid))
                        # Sort by edge weight (co-occurrence strength)
                        neighbor_weights = [(n, self.graph[eid][n].get('weight', 1)) for n in neighbors]
                        neighbor_weights.sort(key=lambda x: -x[1])
                        
                        # Add top 3 neighbors
                        for neighbor_id, weight in neighbor_weights[:3]:
                            if neighbor_id in self.entity_index:
                                neighbor_entity = self.entity_index[neighbor_id]
                                if neighbor_entity.get('canonical_en'):
                                    expansion_terms.add(neighbor_entity['canonical_en'])
                                if neighbor_entity.get('canonical_bn'):
                                    expansion_terms.add(neighbor_entity['canonical_bn'])
        
        return " ".join(sorted(list(expansion_terms)))

    def get_pinned_map(self, query: str, source_lang: str, target_lang: str) -> dict:
        """
        Identify entities and their target-language equivalents for pinning.
        """
        pinned = {}
        if not query or not self.entity_index:
            return pinned
            
        words = query.split()
        for window_size in range(4, 0, -1):
            for i in range(len(words) - window_size + 1):
                phrase = " ".join(words[i:i+window_size])
                lookup_phrase = phrase.lower().strip() if source_lang == 'en' else phrase.strip()
                
                if lookup_phrase in self.name_to_eid:
                    eid = self.name_to_eid[lookup_phrase]
                    entity = self.entity_index[eid]
                    
                    target_name = entity.get('canonical_en') if target_lang == 'en' else entity.get('canonical_bn')
                    if target_name:
                        pinned[phrase] = target_name
        return pinned


def process_query(query: str) -> dict:
    """Convenience function."""
    processor = QueryProcessor()
    return processor.process(query)
