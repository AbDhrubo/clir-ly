"""
Audit Entity Linking
Analyzes missed cross-lingual linking opportunities by comparing top unlinked entities.
"""

import json
import logging
import numpy as np
from typing import Dict, List, Tuple
from pathlib import Path

# Reuse existing modules
from src.preprocessing.labse_linker import get_labse_model, embed_entities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def audit_linking(
    entity_index_path: str = "data/processed/entity_index_linked.json",
    top_k: int = 100
):
    """
    Audit linking quality by checking potential matches among top unlinked entities.
    """
    logger.info("="*60)
    logger.info("ENTITY LINKING AUDIT")
    logger.info("="*60)
    
    # Load index
    with open(entity_index_path, 'r', encoding='utf-8') as f:
        entity_index = json.load(f)
    
    # Get unlinked entities
    unlinked_en = []
    unlinked_bn = []
    
    for record in entity_index.values():
        canonical_en = record.get("canonical_en")
        canonical_bn = record.get("canonical_bn")
        total_mentions = record.get("total_mentions", 0)
        etype = record.get("entity_type", "UNKNOWN")
        
        if canonical_en and not canonical_bn:
            unlinked_en.append((canonical_en, etype, total_mentions))
        elif canonical_bn and not canonical_en:
            unlinked_bn.append((canonical_bn, etype, total_mentions))
            
    # Sort by frequency
    unlinked_en.sort(key=lambda x: -x[2])
    unlinked_bn.sort(key=lambda x: -x[2])
    
    # Take top K
    top_en = [x for x in unlinked_en[:top_k]]
    top_bn = [x for x in unlinked_bn[:top_k]]
    
    logger.info(f"Checking potential matches between Top {top_k} Unlinked entities...")
    
    # Embed
    en_texts = [x[0] for x in top_en]
    bn_texts = [x[0] for x in top_bn]
    
    en_embeddings = embed_entities(en_texts)
    bn_embeddings = embed_entities(bn_texts)
    
    # Compute similarity
    # Normalize
    en_norm = en_embeddings / np.linalg.norm(en_embeddings, axis=1, keepdims=True)
    bn_norm = bn_embeddings / np.linalg.norm(bn_embeddings, axis=1, keepdims=True)
    
    sim_matrix = np.dot(en_norm, bn_norm.T)
    
    # Show closest pairs
    logger.info("\nCLOSEST POTENTIAL MATCHES (that were missed):")
    logger.info("-" * 80)
    logger.info(f"{'English':<30} | {'Bangla':<30} | {'Type':<10} | {'Sim':<5}")
    logger.info("-" * 80)
    
    potential_links = []
    
    for i, (en_text, en_type, _) in enumerate(top_en):
        # Find best Bangla match
        best_idx = np.argmax(sim_matrix[i])
        best_score = sim_matrix[i][best_idx]
        best_bn = top_bn[best_idx][0]
        best_bn_type = top_bn[best_idx][1]
        
        # Consider it a "missed match" if score is decent (>0.7)
        if best_score > 0.7:
            logger.info(f"{en_text[:30]:<30} | {best_bn[:30]:<30} | {en_type[:3]:<3}/{best_bn_type[:3]:<3}   | {best_score:.3f}")
            potential_links.append((en_text, best_bn, best_score))
            
    logger.info("-" * 80)
    logger.info(f"Found {len(potential_links)} potential comparisons with score > 0.7")
    
    # Analysis
    if len(potential_links) > 20:
        logger.info("\nRECOMMENDATION: Consider lowering threshold to 0.75 or 0.8")
    else:
        logger.info("\nRECOMMENDATION: Current linking is likely accurate, dataset simply has disjoint entities")

if __name__ == "__main__":
    audit_linking()
