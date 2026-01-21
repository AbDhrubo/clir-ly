"""
LLM Cross-Linker with LaBSE Fuzzy Matching
Uses LLM-generated id_map.json to directly create cross-lingual links.
Uses LaBSE embeddings for fuzzy Bangla matching when exact match fails.
"""

import json
import logging
import re
import numpy as np
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy load LaBSE
_model = None

def get_labse_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading LaBSE for fuzzy Bangla matching...")
        _model = SentenceTransformer('sentence-transformers/LaBSE')
        logger.info("LaBSE loaded")
    return _model

def normalize_text(text):
    """Normalize text for matching."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'["\'\-\.]', '', text)
    return text

def run_llm_crosslink(
    entity_index_path: str = "data/processed/entity_index.json",
    llm_map_path: str = "data/processed/id_map.json",
    output_path: str = "data/processed/entity_index_llm_linked.json",
    bn_similarity_threshold: float = 0.85  # Threshold for fuzzy Bangla matching
):
    """
    Use LLM mappings to create cross-links with LaBSE fuzzy matching for Bangla.
    """
    
    logger.info("=" * 60)
    logger.info("LLM CROSS-LINKER (with LaBSE Fuzzy Matching)")
    logger.info("=" * 60)
    
    # Load entity index
    logger.info(f"Loading entity index from {entity_index_path}...")
    with open(entity_index_path, 'r', encoding='utf-8') as f:
        entity_index = json.load(f)
    logger.info(f"Loaded {len(entity_index)} entities")
    
    # Load LLM map
    logger.info(f"Loading LLM map from {llm_map_path}...")
    with open(llm_map_path, 'r', encoding='utf-8') as f:
        llm_map = json.load(f)
    logger.info(f"Loaded {len(llm_map)} LLM mappings")
    
    # Build lookups
    en_lookup = {}  # normalized English -> entity_id
    bn_lookup = {}  # exact Bangla -> entity_id
    bn_list = []    # list of (bn_canonical, entity_id) for fuzzy matching
    
    for eid, info in entity_index.items():
        if info.get('canonical_en'):
            en_lookup[normalize_text(info['canonical_en'])] = eid
        if info.get('canonical_bn'):
            bn_lookup[info['canonical_bn']] = eid
            bn_list.append((info['canonical_bn'], eid))
    
    logger.info(f"Built lookups: {len(en_lookup)} EN, {len(bn_lookup)} BN")
    
    # Extract LLM mappings with both EN and BN
    llm_pairs = []
    for raw, mapping in llm_map.items():
        if not isinstance(mapping, dict):
            continue
        en = mapping.get('en')
        bn = mapping.get('bn')
        if en and bn and en != bn:
            llm_pairs.append((raw, en, bn))
    
    logger.info(f"LLM pairs with both EN+BN: {len(llm_pairs)}")
    
    # --- PHASE 1: Exact Matching ---
    llm_links = []
    unmatched_bn = []  # For LaBSE fuzzy matching
    
    for raw, en, bn in llm_pairs:
        # Find English entity (normalized)
        en_id = en_lookup.get(normalize_text(en)) or en_lookup.get(normalize_text(raw))
        
        if not en_id:
            continue
        
        # Try exact Bangla match
        bn_id = bn_lookup.get(bn) or bn_lookup.get(raw)
        
        if bn_id and en_id != bn_id:
            llm_links.append((en_id, bn_id, en, bn))
        elif not bn_id:
            # Save for fuzzy matching
            unmatched_bn.append((en_id, en, bn))
    
    logger.info(f"Phase 1 (exact): {len(llm_links)} links")
    logger.info(f"Phase 2 (fuzzy): {len(unmatched_bn)} need Bangla matching")
    
    # --- PHASE 2: LaBSE Fuzzy Matching for unmatched Bangla ---
    if unmatched_bn and bn_list:
        model = get_labse_model()
        
        # Embed all Bangla canonicals from index
        bn_texts = [bn for bn, eid in bn_list]
        logger.info(f"Embedding {len(bn_texts)} index Bangla entities...")
        bn_embeddings = model.encode(bn_texts, batch_size=128, show_progress_bar=True)
        
        # Embed unmatched LLM Bangla forms
        unmatched_bn_texts = [bn for _, _, bn in unmatched_bn]
        logger.info(f"Embedding {len(unmatched_bn_texts)} LLM Bangla forms...")
        llm_bn_embeddings = model.encode(unmatched_bn_texts, batch_size=128, show_progress_bar=True)
        
        # Compute similarity and find matches
        logger.info("Computing similarities...")
        fuzzy_matches = 0
        for i, (en_id, en, llm_bn) in enumerate(unmatched_bn):
            # Compute cosine similarity with all index Bangla entities
            sims = np.dot(bn_embeddings, llm_bn_embeddings[i])
            best_idx = np.argmax(sims)
            best_sim = sims[best_idx]
            
            if best_sim >= bn_similarity_threshold:
                bn_canonical, bn_id = bn_list[best_idx]
                if en_id != bn_id:
                    llm_links.append((en_id, bn_id, en, llm_bn))
                    fuzzy_matches += 1
        
        logger.info(f"Phase 2: Found {fuzzy_matches} fuzzy Bangla matches")
    
    logger.info(f"Total LLM cross-links found: {len(llm_links)}")
    
    # Apply links
    merged_count = 0
    for en_id, bn_id, en_text, bn_text in llm_links:
        if en_id in entity_index and bn_id in entity_index:
            en_entity = entity_index[en_id]
            bn_entity = entity_index[bn_id]
            
            if not en_entity.get('canonical_bn'):
                en_entity['canonical_bn'] = bn_entity.get('canonical_bn')
                en_entity['aliases_bn'] = bn_entity.get('aliases_bn', [])
                merged_count += 1
            
            en_entity['cross_linked'] = True
            en_entity['linked_from_llm'] = True
    
    logger.info(f"Applied {merged_count} new LLM-based cross-links")
    
    total_linked = sum(1 for e in entity_index.values() if e.get('canonical_en') and e.get('canonical_bn'))
    logger.info(f"Total cross-linked entities: {total_linked}")
    
    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entity_index, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved to {output_path}")
    
    logger.info("=" * 60)
    logger.info("LLM CROSS-LINKING COMPLETE")
    logger.info("=" * 60)
    
    return merged_count, total_linked

if __name__ == "__main__":
    run_llm_crosslink()
