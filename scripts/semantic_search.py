#!/usr/bin/env python3
"""
Module C - Semantic Search
Multilingual embedding-based search using sentence-transformers
Single script: query → Module B → semantic cross-lingual search → JSON/CSV results

Usage:
    python semantic_search.py                           # Default: LaBSE
    python semantic_search.py --model labse             # LaBSE (multilingual, good for many languages)
    python semantic_search.py --model xlmr              # XLM-R (state-of-the-art, 100+ languages)
    python semantic_search.py --model mbert             # mBERT (older but stable)
    python semantic_search.py --model mt5               # mT5 (older but stable)
"""

import sys
import json
import csv
import time
import argparse
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.processor import QueryProcessor

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("[ERROR] sentence-transformers or scikit-learn not installed")
    print("Install with: pip install sentence-transformers scikit-learn")
    sys.exit(1)


# Model configurations
MODELS = {
    'labse': {
        'name': 'sentence-transformers/LaBSE',
        'description': 'Language-agnostic BERT - multilingual, good for many languages',
    },
    'xlmr': {
        'name': 'FacebookAI/xlm-roberta-base',
        'description': 'XLM-RoBERTa - state-of-the-art, supports 100+ languages',
    },
    'mbert': {
        'name': 'bert-base-multilingual-cased',
        'description': 'Multilingual BERT - older but stable',
    },
    'mt5': {
        'name': 'google/mt5-base',
        'description': 'mT5 - older but stable',
    },
}


def load_documents(filepath="notebooks/data/articles_with_ner.jsonl"):
    """Load all documents (EN + BN)."""
    docs = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    docs.append(json.loads(line))
        return docs
    except Exception as e:
        print(f"Error loading documents: {e}")
        return []


def search_crosslingual(docs: List[Dict], query: str, query_lang: str, model, k: int = 10):
    """
    Full pipeline: raw query → Module B processing → semantic cross-lingual search
    
    Uses multilingual embeddings (LaBSE or multilingual SBERT) for matching
    """
    processor = QueryProcessor()
    processed = processor.process(query)
    
    detected_lang = processed['language']
    normalized_query = processed['normalized']
    translated_query = processed['translated']
    
    en_results = []
    bn_results = []
    
    # Encode query
    query_embedding = model.encode(normalized_query)
    
    # Search 1: Original language
    if detected_lang == 'en':
        # Get English documents
        en_docs_list = [(i, doc) for i, doc in enumerate(docs) if doc.get('language') == 'en']
        if en_docs_list:
            # Encode English docs
            en_texts = [f"{doc['title']} {doc['body']}" for _, doc in en_docs_list]
            en_embeddings = model.encode(en_texts)
            
            # Calculate similarity
            similarities = cosine_similarity([query_embedding], en_embeddings)[0]
            
            # Sort by similarity
            sorted_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)
            
            for rank, idx in enumerate(sorted_indices[:20], 1):
                doc_idx, doc = en_docs_list[idx]
                score = similarities[idx] * 100  # Convert to percentage
                en_results.append({
                    'rank': rank,
                    'title': doc.get('title', '')[:80],
                    'body': doc.get('body', '')[:150],
                    'language': 'en',
                    'score': float(score),
                    'url': doc.get('url', ''),
                })
        
        # Search 2: Translated to Bangla
        if translated_query:
            bn_docs_list = [(i, doc) for i, doc in enumerate(docs) if doc.get('language') == 'bn']
            if bn_docs_list:
                # Encode translated query
                query_embedding_bn = model.encode(translated_query)
                
                # Encode Bangla docs
                bn_texts = [f"{doc['title']} {doc['body']}" for _, doc in bn_docs_list]
                bn_embeddings = model.encode(bn_texts)
                
                # Calculate similarity
                similarities = cosine_similarity([query_embedding_bn], bn_embeddings)[0]
                
                # Sort by similarity
                sorted_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)
                
                for rank, idx in enumerate(sorted_indices[:20], 1):
                    doc_idx, doc = bn_docs_list[idx]
                    score = similarities[idx] * 100
                    bn_results.append({
                        'rank': rank,
                        'title': doc.get('title', '')[:80],
                        'body': doc.get('body', '')[:150],
                        'language': 'bn',
                        'score': float(score),
                        'url': doc.get('url', ''),
                    })
    else:
        # Bangla query
        bn_docs_list = [(i, doc) for i, doc in enumerate(docs) if doc.get('language') == 'bn']
        if bn_docs_list:
            bn_texts = [f"{doc['title']} {doc['body']}" for _, doc in bn_docs_list]
            bn_embeddings = model.encode(bn_texts)
            
            similarities = cosine_similarity([query_embedding], bn_embeddings)[0]
            sorted_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)
            
            for rank, idx in enumerate(sorted_indices[:20], 1):
                doc_idx, doc = bn_docs_list[idx]
                score = similarities[idx] * 100
                bn_results.append({
                    'rank': rank,
                    'title': doc.get('title', '')[:80],
                    'body': doc.get('body', '')[:150],
                    'language': 'bn',
                    'score': float(score),
                    'url': doc.get('url', ''),
                })
        
        # Search 2: Translated to English
        if translated_query:
            en_docs_list = [(i, doc) for i, doc in enumerate(docs) if doc.get('language') == 'en']
            if en_docs_list:
                query_embedding_en = model.encode(translated_query)
                
                en_texts = [f"{doc['title']} {doc['body']}" for _, doc in en_docs_list]
                en_embeddings = model.encode(en_texts)
                
                similarities = cosine_similarity([query_embedding_en], en_embeddings)[0]
                sorted_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)
                
                for rank, idx in enumerate(sorted_indices[:20], 1):
                    doc_idx, doc = en_docs_list[idx]
                    score = similarities[idx] * 100
                    en_results.append({
                        'rank': rank,
                        'title': doc.get('title', '')[:80],
                        'body': doc.get('body', '')[:150],
                        'language': 'en',
                        'score': float(score),
                        'url': doc.get('url', ''),
                    })
    
    # Merge results by score
    combined = []
    en_idx = bn_idx = 0
    
    while len(combined) < 10 and (en_idx < len(en_results) or bn_idx < len(bn_results)):
        if en_idx < len(en_results) and bn_idx < len(bn_results):
            if en_results[en_idx]['score'] >= bn_results[bn_idx]['score']:
                result = en_results[en_idx].copy()
                result['rank'] = len(combined) + 1
                combined.append(result)
                en_idx += 1
            else:
                result = bn_results[bn_idx].copy()
                result['rank'] = len(combined) + 1
                combined.append(result)
                bn_idx += 1
        elif en_idx < len(en_results):
            result = en_results[en_idx].copy()
            result['rank'] = len(combined) + 1
            combined.append(result)
            en_idx += 1
        else:
            result = bn_results[bn_idx].copy()
            result['rank'] = len(combined) + 1
            combined.append(result)
            bn_idx += 1
    
    return {
        'raw_query': query,
        'language': detected_lang,
        'normalized': normalized_query,
        'translated': translated_query if translated_query != normalized_query else None,
        'en_results': en_results[:5],
        'bn_results': bn_results[:5],
        'combined_top10': combined[:10],
    }


def main():
    parser = argparse.ArgumentParser(description='Semantic search with configurable embedding models')
    parser.add_argument(
        '--model',
        choices=MODELS.keys(),
        default='labse',
        help=f'Embedding model to use (default: labse)\nOptions: {", ".join(MODELS.keys())}'
    )
    args = parser.parse_args()
    
    model_config = MODELS[args.model]
    model_name = model_config['name']
    
    print("\n[*] Loading documents...")
    docs = load_documents()
    if not docs:
        print("[ERROR] No documents loaded")
        return 1
    
    en_count = sum(1 for d in docs if d.get('language') == 'en')
    bn_count = sum(1 for d in docs if d.get('language') == 'bn')
    print(f"[OK] {len(docs)} documents ({en_count} EN, {bn_count} BN)\n")
    
    print(f"[*] Loading embedding model: {args.model}")
    print(f"    {model_config['description']}")
    try:
        model = SentenceTransformer(model_name)
        print("[OK] Model loaded\n")
    except Exception as e:
        print(f"[ERROR] Could not load model: {e}")
        return 1
    
    print("[*] Initializing QueryProcessor (Module B)...")
    processor = QueryProcessor()
    print("[OK] Module B ready\n")
    
    # Test queries: 5 English + 5 Bangla
    test_queries = [
        # English
        "Bangladesh politics",
        "cricket news",
        "education system",
        "dhaka economy",
        "energy crisis",
        # Bangla
        "বাংলাদেশের রাজনীতি",
        "ক্রিকেট সংবাদ",
        "শিক্ষা ব্যবস্থা",
        "ঢাকার অর্থনীতি",
        "শক্তি সংকট",
    ]
    
    print(f"[*] Running {len(test_queries)} queries through semantic search...\n")
    
    results_list = []
    for i, query in enumerate(test_queries, 1):
        print(f"[{i:2d}/10] {query[:40]:40s} ...", end=" ", flush=True)
        
        start = time.time()
        result = search_crosslingual(docs, query, query[0], model, k=10)
        elapsed = (time.time() - start) * 1000
        
        result['execution_time_ms'] = elapsed
        results_list.append(result)
        
        print(f"{elapsed:.1f}ms")
    
    # Output to JSON
    json_path = f"results/semantic_results_{args.model}.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_list, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON saved to {json_path}")
    
    # Output to CSV
    csv_path = f"results/semantic_results_{args.model}.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Query', 'Lang', 'Translated', 'Rank-1 EN', 'Score EN', 'Rank-1 BN', 'Score BN', 'Time(ms)'])
        
        for r in results_list:
            top_en = r['en_results'][0]['title'] if r['en_results'] else '-'
            score_en = r['en_results'][0]['score'] if r['en_results'] else 0
            top_bn = r['bn_results'][0]['title'] if r['bn_results'] else '-'
            score_bn = r['bn_results'][0]['score'] if r['bn_results'] else 0
            
            writer.writerow([
                r['raw_query'],
                r['language'],
                r['translated'] or '-',
                top_en,
                f"{score_en:.1f}%",
                top_bn,
                f"{score_bn:.1f}%",
                f"{r['execution_time_ms']:.1f}",
            ])
    
    print(f"[OK] CSV saved to {csv_path}\n")
    
    # Print summary
    print("="*70)
    print(f"SEMANTIC SEARCH RESULTS SUMMARY ({args.model.upper()})")
    print("="*70 + "\n")
    
    for r in results_list:
        print(f"Query: {r['raw_query']} ({r['language'].upper()})")
        if r['translated']:
            print(f"  Translation: {r['translated']}")
        print(f"  Time: {r['execution_time_ms']:.1f}ms")
        print(f"  Top 10 Results:")
        
        for res in r['combined_top10'][:5]:
            rank = res.get('rank', '?')
            print(f"    {rank}. [{res['score']:.1f}%] {res['title']} ({res['language']})")
        
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
