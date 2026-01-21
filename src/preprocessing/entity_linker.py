"""
Entity Linker Module
Handles entity deduplication, normalization, and cross-lingual linking.
"""

import json
import re
import logging
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Try to import optional dependencies
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not installed. Install with: pip install rapidfuzz")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EntityRecord:
    """Represents a canonical entity with all its variants."""
    entity_id: str
    canonical_en: Optional[str] = None
    canonical_bn: Optional[str] = None
    aliases: List[str] = field(default_factory=list)
    entity_type: str = "UNKNOWN"
    article_count: int = 0
    total_mentions: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EntityNormalizer:
    """Normalizes entity surface forms."""
    
    # Common prefixes/suffixes to strip
    STRIP_PREFIXES = ["the ", "a ", "an "]
    STRIP_SUFFIXES = ["'s", "'s"]
    
    # Abbreviation mappings (expandable)
    ABBREVIATIONS = {
        "bnp": "bangladesh nationalist party",
        "al": "awami league",
        "jp": "jatiya party",
        "ec": "election commission",
        "pm": "prime minister",
        "mp": "member of parliament",
        "dc": "deputy commissioner",
        "sp": "superintendent of police",
        "rab": "rapid action battalion",
        "bsec": "bangladesh securities and exchange commission",
        "dse": "dhaka stock exchange",
        "icb": "investment corporation of bangladesh",
        "du": "dhaka university",
        "buet": "bangladesh university of engineering and technology",
    }
    
    # Load LLM Map if available
    LLM_MAP = {}
    try:
        with open("data/processed/id_map.json", "r", encoding="utf-8") as f:
            LLM_MAP = json.load(f)
    except Exception:
        pass

    @classmethod
    def normalize(cls, text: str, entity_type: str = None) -> str:
        """Normalize entity text to canonical form."""
        if not text:
            return ""
        
        # 1. LLM Look-ahead (Fast path)
        # Check raw text directly
        if text in cls.LLM_MAP:
            mapping = cls.LLM_MAP[text]
            if isinstance(mapping, dict):
                # Return English canonical if available, else Bangla
                return mapping.get("en") or mapping.get("bn") or text

        # Basic cleanup
        normalized = text.strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        
        # Remove quotes
        normalized = normalized.strip('"\'""''')
        
        # 2. LLM Look-ahead (Normalized path)
        if normalized in cls.LLM_MAP:
             mapping = cls.LLM_MAP[normalized]
             if isinstance(mapping, dict):
                return mapping.get("en") or mapping.get("bn") or normalized
        
        # FILTER: Skip single characters (noise)
        if len(normalized) <= 1:
            return ""
            
        # FILTER: Skip entities starting/ending with known garbage chars
        if normalized in ["এর", "কে", "যে", "ও"]: # Common particles
            return ""


        
        # Strip common prefixes (for ORG)
        if entity_type == "ORG":
            lower = normalized.lower()
            for prefix in cls.STRIP_PREFIXES:
                if lower.startswith(prefix):
                    normalized = normalized[len(prefix):]
                    break
        
        # Strip possessive suffixes
        for suffix in cls.STRIP_SUFFIXES:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        return normalized.strip()
    
    @classmethod
    def get_canonical_key(cls, text: str) -> str:
        """Generate a key for clustering similar entities."""
        key = cls.normalize(text).lower()
        # Remove punctuation for matching
        key = re.sub(r'[^\w\s]', '', key)
        key = re.sub(r'\s+', ' ', key).strip()
        return key


class EntityClusterer:
    """Clusters similar entities using fuzzy matching."""
    
    def __init__(self, similarity_threshold: float = 85.0):
        self.threshold = similarity_threshold
        self.clusters: Dict[str, Set[str]] = defaultdict(set)
        self.canonical_forms: Dict[str, str] = {}
        
    def cluster_entities(self, entities: List[Tuple[str, str, int]]) -> Dict[str, List[str]]:
        """
        Cluster similar entities.
        
        Args:
            entities: List of (entity_text, entity_type, count) tuples
            
        Returns:
            Dict mapping canonical form to list of variants
        """
        if not RAPIDFUZZ_AVAILABLE:
            logger.warning("rapidfuzz not available, using exact matching only")
            return self._exact_cluster(entities)
        
        # Group by entity type first
        by_type: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for text, etype, count in entities:
            by_type[etype].append((text, count))
        
        all_clusters = {}
        
        for etype, type_entities in by_type.items():
            logger.info(f"Clustering {len(type_entities)} {etype} entities...")
            clusters = self._fuzzy_cluster(type_entities)
            
            for canonical, variants in clusters.items():
                all_clusters[canonical] = {
                    "type": etype,
                    "variants": variants
                }
        
        return all_clusters
    
    def _fuzzy_cluster(self, entities: List[Tuple[str, int]]) -> Dict[str, List[str]]:
        """Cluster using fuzzy string matching."""
        # Sort by frequency (most common first)
        sorted_entities = sorted(entities, key=lambda x: -x[1])
        
        clusters: Dict[str, List[str]] = {}
        assigned: Set[str] = set()
        
        for text, count in sorted_entities:
            if text in assigned:
                continue
            
            # Normalize for matching
            key = EntityNormalizer.get_canonical_key(text)
            if not key:
                continue
            
            # Find similar entities
            similar = [text]
            
            for other_text, other_count in sorted_entities:
                if other_text == text or other_text in assigned:
                    continue
                
                other_key = EntityNormalizer.get_canonical_key(other_text)
                if not other_key:
                    continue
                
                # Check similarity
                ratio = fuzz.ratio(key, other_key)
                if ratio >= self.threshold:
                    similar.append(other_text)
                    assigned.add(other_text)
            
            # Use most frequent as canonical
            clusters[text] = similar
            assigned.add(text)
        
        return clusters
    
    def _exact_cluster(self, entities: List[Tuple[str, str, int]]) -> Dict[str, List[str]]:
        """Fallback: cluster by exact normalized key."""
        key_to_entities: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        
        for text, etype, count in entities:
            key = EntityNormalizer.get_canonical_key(text)
            if key:
                key_to_entities[(key, etype)].append((text, count))
        
        clusters = {}
        for (key, etype), variants in key_to_entities.items():
            # Sort by count, pick most frequent as canonical
            sorted_variants = sorted(variants, key=lambda x: -x[1])
            canonical = sorted_variants[0][0]
            clusters[canonical] = {
                "type": etype,
                "variants": [v[0] for v in sorted_variants]
            }
        
        return clusters


class CrossLingualLinker:
    """Links entities across English and Bangla."""
    
    # Known entity pairs (seed dictionary)
    SEED_PAIRS = {
        # Locations
        "bangladesh": "বাংলাদেশ",
        "dhaka": "ঢাকা",
        "chattogram": "চট্টগ্রাম",
        "chittagong": "চট্টগ্রাম",
        "sylhet": "সিলেট",
        "rajshahi": "রাজশাহী",
        "khulna": "খুলনা",
        "barishal": "বরিশাল",
        "rangpur": "রংপুর",
        "mymensingh": "ময়মনসিংহ",
        "comilla": "কুমিল্লা",
        "cumilla": "কুমিল্লা",
        "india": "ভারত",
        "pakistan": "পাকিস্তান",
        "kolkata": "কলকাতা",
        
        # Political parties
        "bnp": "বিএনপি",
        "bangladesh nationalist party": "বাংলাদেশ জাতীয়তাবাদী দল",
        "awami league": "আওয়ামী লীগ",
        "jatiya party": "জাতীয় পার্টি",
        "jamaat-e-islami": "জামায়াতে ইসলামী",
        "jamaat": "জামায়াত",
        
        # Organizations
        "election commission": "নির্বাচন কমিশন",
        "parliament": "সংসদ",
        "supreme court": "সুপ্রিম কোর্ট",
        "high court": "হাইকোর্ট",
        "dhaka university": "ঢাকা বিশ্ববিদ্যালয়",
        
        # People (notable)
        "sheikh hasina": "শেখ হাসিনা",
        "khaleda zia": "খালেদা জিয়া",
        "tarique rahman": "তারেক রহমান",
        "muhammad yunus": "মুহাম্মদ ইউনূস",
        "ziaur rahman": "জিয়াউর রহমান",
    }
    
    def __init__(self):
        # Build reverse mapping
        self.en_to_bn = {k.lower(): v for k, v in self.SEED_PAIRS.items()}
        self.bn_to_en = {v: k for k, v in self.SEED_PAIRS.items()}
    
    def find_link(self, entity: str, source_lang: str) -> Optional[str]:
        """Find cross-lingual link for an entity."""
        key = entity.lower().strip()
        
        if source_lang == "en":
            return self.en_to_bn.get(key)
        else:
            return self.bn_to_en.get(entity.strip())
    
    def add_pair(self, en: str, bn: str):
        """Add a new entity pair."""
        self.en_to_bn[en.lower()] = bn
        self.bn_to_en[bn] = en.lower()


class EntityLinker:
    """Main class for entity linking pipeline."""
    
    def __init__(self, similarity_threshold: float = 85.0):
        self.normalizer = EntityNormalizer()
        self.clusterer = EntityClusterer(similarity_threshold)
        self.cross_linker = CrossLingualLinker()
        self.entity_index: Dict[str, EntityRecord] = {}
        self.surface_to_id: Dict[str, str] = {}
        
    def build_index(self, articles: List[Dict[str, Any]]) -> Dict[str, EntityRecord]:
        """
        Build entity index from articles.
        
        Args:
            articles: List of article dicts with 'named_entities' and 'language' fields
            
        Returns:
            Dict mapping entity_id to EntityRecord
        """
        logger.info("Extracting entities from articles...")
        
        # Collect all entities with counts
        en_entities: Counter = Counter()
        bn_entities: Counter = Counter()
        entity_types: Dict[str, str] = {}
        
        for article in articles:
            lang = article.get("language", "en")
            entities = article.get("named_entities", [])
            
            for ent in entities:
                text = ent.get("text", "").strip()
                etype = ent.get("label", "UNKNOWN")
                
                if len(text) < 2:  # Skip single chars
                    continue
                
                if lang == "en":
                    en_entities[text] += 1
                else:
                    bn_entities[text] += 1
                
                entity_types[text] = etype
        
        logger.info(f"Found {len(en_entities)} unique English entities")
        logger.info(f"Found {len(bn_entities)} unique Bangla entities")
        
        # Cluster English entities
        logger.info("Clustering English entities...")
        en_list = [(text, entity_types.get(text, "UNKNOWN"), count) 
                   for text, count in en_entities.items()]
        en_clusters = self.clusterer.cluster_entities(en_list)
        
        # Cluster Bangla entities
        logger.info("Clustering Bangla entities...")
        bn_list = [(text, entity_types.get(text, "UNKNOWN"), count) 
                   for text, count in bn_entities.items()]
        bn_clusters = self.clusterer.cluster_entities(bn_list)
        
        # Build entity records
        logger.info("Building entity index...")
        entity_id = 0
        
        # Process English clusters
        for canonical, info in en_clusters.items():
            eid = f"E{entity_id:05d}"
            entity_id += 1
            
            variants = info["variants"] if isinstance(info, dict) else info
            etype = info.get("type", "UNKNOWN") if isinstance(info, dict) else entity_types.get(canonical, "UNKNOWN")
            
            total_mentions = sum(en_entities[v] for v in variants)
            article_count = len(set(v for v in variants))  # Approximate
            
            # Try to find Bangla link
            bn_link = self.cross_linker.find_link(canonical, "en")
            
            record = EntityRecord(
                entity_id=eid,
                canonical_en=canonical,
                canonical_bn=bn_link,
                aliases=variants if len(variants) > 1 else [],
                entity_type=etype,
                article_count=article_count,
                total_mentions=total_mentions
            )
            
            self.entity_index[eid] = record
            
            # Map all variants to this ID
            for variant in variants:
                self.surface_to_id[variant.lower()] = eid
        
        # Process Bangla clusters (link to English if possible)
        for canonical, info in bn_clusters.items():
            variants = info["variants"] if isinstance(info, dict) else info
            etype = info.get("type", "UNKNOWN") if isinstance(info, dict) else entity_types.get(canonical, "UNKNOWN")
            
            # Check if already linked via English
            en_link = self.cross_linker.find_link(canonical, "bn")
            if en_link and en_link.lower() in self.surface_to_id:
                eid = self.surface_to_id[en_link.lower()]
                # Update existing record
                self.entity_index[eid].canonical_bn = canonical
                self.entity_index[eid].aliases.extend(variants)
                self.entity_index[eid].total_mentions += sum(bn_entities[v] for v in variants)
            else:
                # Create new record for Bangla-only entity
                eid = f"E{entity_id:05d}"
                entity_id += 1
                
                total_mentions = sum(bn_entities[v] for v in variants)
                
                record = EntityRecord(
                    entity_id=eid,
                    canonical_en=None,
                    canonical_bn=canonical,
                    aliases=variants if len(variants) > 1 else [],
                    entity_type=etype,
                    article_count=len(variants),
                    total_mentions=total_mentions
                )
                
                self.entity_index[eid] = record
            
            # Map all variants to this ID
            for variant in variants:
                self.surface_to_id[variant] = eid
        
        logger.info(f"Built index with {len(self.entity_index)} canonical entities")
        return self.entity_index
    
    def enhance_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add entity IDs to article entities."""
        enhanced = []
        
        for article in articles:
            article_copy = article.copy()
            entities = article_copy.get("named_entities", [])
            
            enhanced_entities = []
            for ent in entities:
                ent_copy = ent.copy()
                text = ent.get("text", "").strip()
                
                # Look up entity ID
                eid = self.surface_to_id.get(text.lower()) or self.surface_to_id.get(text)
                if eid:
                    ent_copy["entity_id"] = eid
                
                enhanced_entities.append(ent_copy)
            
            article_copy["named_entities"] = enhanced_entities
            enhanced.append(article_copy)
        
        return enhanced
    
    def save_index(self, filepath: str):
        """Save entity index to JSON."""
        data = {eid: record.to_dict() for eid, record in self.entity_index.items()}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved entity index to {filepath}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the entity index."""
        total = len(self.entity_index)
        with_en = sum(1 for e in self.entity_index.values() if e.canonical_en)
        with_bn = sum(1 for e in self.entity_index.values() if e.canonical_bn)
        cross_linked = sum(1 for e in self.entity_index.values() if e.canonical_en and e.canonical_bn)
        
        by_type = Counter(e.entity_type for e in self.entity_index.values())
        
        return {
            "total_entities": total,
            "with_english": with_en,
            "with_bangla": with_bn,
            "cross_linked": cross_linked,
            "by_type": dict(by_type)
        }


def run_entity_linking(
    input_path: str = "notebooks/data/articles_with_ner.jsonl",
    output_articles: str = "data/processed/articles_enhanced.jsonl",
    output_index: str = "data/processed/entity_index.json"
):
    """Run the complete entity linking pipeline."""
    
    logger.info("="*60)
    logger.info("ENTITY LINKING PIPELINE")
    logger.info("="*60)
    
    # Load articles
    logger.info(f"Loading articles from {input_path}...")
    articles = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            articles.append(json.loads(line))
    logger.info(f"Loaded {len(articles)} articles")
    
    # Build entity index
    linker = EntityLinker(similarity_threshold=85.0)
    linker.build_index(articles)
    
    # Print stats
    stats = linker.get_stats()
    logger.info("\n" + "="*60)
    logger.info("ENTITY INDEX STATISTICS")
    logger.info("="*60)
    logger.info(f"Total canonical entities: {stats['total_entities']}")
    logger.info(f"With English form: {stats['with_english']}")
    logger.info(f"With Bangla form: {stats['with_bangla']}")
    logger.info(f"Cross-linked (EN+BN): {stats['cross_linked']}")
    logger.info(f"By type: {stats['by_type']}")
    
    # Enhance articles
    logger.info("\nEnhancing articles with entity IDs...")
    enhanced = linker.enhance_articles(articles)
    
    # Save outputs
    Path(output_articles).parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving enhanced articles to {output_articles}...")
    with open(output_articles, 'w', encoding='utf-8') as f:
        for article in enhanced:
            f.write(json.dumps(article, ensure_ascii=False) + '\n')
    
    linker.save_index(output_index)
    
    logger.info("\n" + "="*60)
    logger.info("ENTITY LINKING COMPLETE")
    logger.info("="*60)
    
    return linker, stats


if __name__ == "__main__":
    run_entity_linking()
