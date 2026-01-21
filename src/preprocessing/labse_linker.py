"""
Cross-Lingual Entity Linker using LaBSE embeddings.
Matches English and Bangla entities by semantic similarity.
"""

import json
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy load to avoid import errors
_model = None

def get_labse_model():
    """Lazy load LaBSE model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading LaBSE model (this may take a minute)...")
        _model = SentenceTransformer('sentence-transformers/LaBSE')
        logger.info("LaBSE model loaded")
    return _model


def embed_entities(entities: List[str], batch_size: int = 128) -> np.ndarray:
    """Embed a list of entity strings using LaBSE."""
    model = get_labse_model()
    embeddings = model.encode(entities, batch_size=batch_size, show_progress_bar=True)
    return embeddings


def find_cross_lingual_matches(
    en_entities: List[str],
    bn_entities: List[str],
    en_types: Dict[str, str],
    bn_types: Dict[str, str],
    similarity_threshold: float = 0.85,
    top_k: int = 3
) -> List[Tuple[str, str, float]]:
    """
    Find matching entity pairs between English and Bangla using embeddings.
    
    Args:
        en_entities: List of English entity texts
        bn_entities: List of Bangla entity texts
        en_types: Dict mapping EN entity -> type
        bn_types: Dict mapping BN entity -> type
        similarity_threshold: Minimum cosine similarity for a match
        top_k: Number of top candidates to consider per entity
        
    Returns:
        List of (en_entity, bn_entity, similarity_score) tuples
    """
    if not en_entities or not bn_entities:
        return []
    
    logger.info(f"Embedding {len(en_entities)} English entities...")
    en_embeddings = embed_entities(en_entities)
    
    logger.info(f"Embedding {len(bn_entities)} Bangla entities...")
    bn_embeddings = embed_entities(bn_entities)
    
    # Normalize for cosine similarity
    en_norm = en_embeddings / np.linalg.norm(en_embeddings, axis=1, keepdims=True)
    bn_norm = bn_embeddings / np.linalg.norm(bn_embeddings, axis=1, keepdims=True)
    
    # Compute similarity matrix (EN x BN)
    logger.info("Computing similarity matrix...")
    similarity_matrix = np.dot(en_norm, bn_norm.T)
    
    # Find matches
    matches = []
    matched_bn = set()
    
    for en_idx, en_entity in enumerate(en_entities):
        en_type = en_types.get(en_entity, "UNKNOWN")
        
        # Get top-k most similar Bangla entities
        similarities = similarity_matrix[en_idx]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        for bn_idx in top_indices:
            if bn_idx in matched_bn:
                continue
                
            bn_entity = bn_entities[bn_idx]
            bn_type = bn_types.get(bn_entity, "UNKNOWN")
            
            # Only match same entity types
            if en_type != bn_type:
                continue
            
            sim_score = similarities[bn_idx]
            if sim_score >= similarity_threshold:
                matches.append((en_entity, bn_entity, float(sim_score)))
                matched_bn.add(bn_idx)
                break  # One match per EN entity
    
    # Sort by similarity
    matches.sort(key=lambda x: -x[2])
    
    return matches


def run_labse_linking(
    entity_index_path: str = "data/processed/entity_index.json",
    llm_linked_path: str = "data/processed/entity_index_llm_linked.json",
    output_path: str = "data/processed/entity_index_linked.json",
    similarity_threshold: float = 0.75
) -> Dict[str, Any]:
    """
    Run LaBSE-based cross-lingual entity linking.
    
    If llm_linked_path exists, use it (has LLM cross-links).
    Otherwise fall back to entity_index_path.
    """
    logger.info("="*60)
    logger.info("LABSE CROSS-LINGUAL ENTITY LINKING")
    logger.info("="*60)
    
    # Load entity index
    logger.info(f"Loading entity index from {entity_index_path}...")
    with open(entity_index_path, 'r', encoding='utf-8') as f:
        entity_index = json.load(f)
    
    logger.info(f"Loaded {len(entity_index)} entities")
    
    # Separate EN-only and BN-only entities
    en_only = {}
    bn_only = {}
    already_linked = 0
    
    for eid, record in entity_index.items():
        has_en = record.get("canonical_en") is not None
        has_bn = record.get("canonical_bn") is not None
        
        if has_en and has_bn:
            already_linked += 1
        elif has_en:
            en_only[record["canonical_en"]] = (eid, record.get("entity_type", "UNKNOWN"))
        elif has_bn:
            bn_only[record["canonical_bn"]] = (eid, record.get("entity_type", "UNKNOWN"))
    
    logger.info(f"Already linked: {already_linked}")
    logger.info(f"English-only: {len(en_only)}")
    logger.info(f"Bangla-only: {len(bn_only)}")
    
    if not en_only or not bn_only:
        logger.warning("No entities to link!")
        return {"new_links": 0, "total_linked": already_linked}
    
    # Prepare for matching
    en_entities = list(en_only.keys())
    bn_entities = list(bn_only.keys())
    
    en_types = {e: info[1] for e, info in en_only.items()}
    bn_types = {e: info[1] for e, info in bn_only.items()}
    
    # Find matches
    logger.info(f"\nFinding matches with threshold={similarity_threshold}...")
    matches = find_cross_lingual_matches(
        en_entities, bn_entities,
        en_types, bn_types,
        similarity_threshold=similarity_threshold
    )
    
    logger.info(f"Found {len(matches)} new cross-lingual matches")
    
    # Update entity index - merge BN entities into EN entities
    merged_count = 0
    for en_text, bn_text, score in matches:
        en_eid, _ = en_only[en_text]
        bn_eid, _ = bn_only[bn_text]
        
        # Add BN canonical to EN entity
        entity_index[en_eid]["canonical_bn"] = bn_text
        
        # Add BN aliases to EN entity
        bn_aliases = entity_index[bn_eid].get("aliases", [])
        if bn_aliases:
            entity_index[en_eid].setdefault("aliases", []).extend(bn_aliases)
        
        # Add BN count to EN entity
        entity_index[en_eid]["total_mentions"] = (
            entity_index[en_eid].get("total_mentions", 0) +
            entity_index[bn_eid].get("total_mentions", 0)
        )
        
        # Store similarity score
        entity_index[en_eid]["cross_lingual_score"] = score
        
        # Remove BN entity (it's now merged)
        del entity_index[bn_eid]
        merged_count += 1
    
    # Save updated index
    logger.info(f"\nSaving updated index to {output_path}...")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(entity_index, f, ensure_ascii=False, indent=2)
    
    # Print sample matches
    logger.info("\n" + "="*60)
    logger.info("SAMPLE MATCHES (Top 20)")
    logger.info("="*60)
    for en_text, bn_text, score in matches[:20]:
        logger.info(f"  {en_text} ↔ {bn_text} ({score:.3f})")
    
    # Stats
    total_linked = already_linked + len(matches)
    stats = {
        "already_linked": already_linked,
        "new_links": len(matches),
        "total_linked": total_linked,
        "entities_merged": merged_count,
        "final_entity_count": len(entity_index)
    }
    
    logger.info("\n" + "="*60)
    logger.info("LINKING COMPLETE")
    logger.info("="*60)
    logger.info(f"New cross-lingual links: {len(matches)}")
    logger.info(f"Total linked entities: {total_linked}")
    logger.info(f"Final entity count: {len(entity_index)}")
    
    return stats


if __name__ == "__main__":
    run_labse_linking()
