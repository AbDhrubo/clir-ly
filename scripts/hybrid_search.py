#!/usr/bin/env python3
"""
Module C - Hybrid Ranking
Combines BM25 + Fuzzy + Semantic with weighted scoring
Single script: query → Module B → all three strategies → weighted combination → JSON/CSV results
"""

import sys
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.processor import QueryProcessor

try:
    from rank_bm25 import BM25Okapi
    from fuzzywuzzy import fuzz
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("[ERROR] Dependencies not installed")
    print("Install with: pip install rank-bm25 fuzzywuzzy sentence-transformers scikit-learn")
    sys.exit(1)


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


def build_indexes(docs: List[Dict]):
    """Build BM25 indexes for EN and BN documents."""
    en_docs = [d for d in docs if d.get('language') == 'en']
    bn_docs = [d for d in docs if d.get('language') == 'bn']
    
    en_corpus = [f"{d['title']} {d['body']}".split() for d in en_docs]
    bn_corpus = [f"{d['title']} {d['body']}".split() for d in bn_docs]
    
    return {
        'en_bm25': BM25Okapi(en_corpus),
        'en_docs': en_docs,
        'bn_bm25': BM25Okapi(bn_corpus),
        'bn_docs': bn_docs,
    }


def search_hybrid(
    docs: List[Dict],
    indexes: Dict,
    query: str,
    embedding_model,
    weights: Dict = None,
    k: int = 10
):
    """
    Hybrid search combining BM25 + Fuzzy + Semantic
    Default weights: BM25=0.2, Fuzzy=0.1, Semantic=0.7
    """
    if weights is None:
        weights = {'bm25': 0.2, 'fuzzy': 0.1, 'semantic': 0.7}
    
    processor = QueryProcessor()
    processed = processor.process(query)
    
    detected_lang = processed['language']
    normalized_query = processed['normalized']
    translated_query = processed['translated']
    
    # === Strategy 1: BM25 ===
    bm25_scores = {}
    query_terms = normalized_query.split()
    
    if detected_lang == 'en':
        bm25_results = indexes['en_bm25'].get_scores(query_terms)
        for idx, score in enumerate(bm25_results):
            doc_id = ('en', idx)
            bm25_scores[doc_id] = score
        
        if translated_query:
            trans_terms = translated_query.split()
            bm25_results = indexes['bn_bm25'].get_scores(trans_terms)
            for idx, score in enumerate(bm25_results):
                doc_id = ('bn', idx)
                bm25_scores[doc_id] = score
    else:
        bm25_results = indexes['bn_bm25'].get_scores(query_terms)
        for idx, score in enumerate(bm25_results):
            doc_id = ('bn', idx)
            bm25_scores[doc_id] = score
        
        if translated_query:
            trans_terms = translated_query.split()
            bm25_results = indexes['en_bm25'].get_scores(trans_terms)
            for idx, score in enumerate(bm25_results):
                doc_id = ('en', idx)
                bm25_scores[doc_id] = score
    
    # === Strategy 2: Fuzzy ===
    fuzzy_scores = {}
    
    if detected_lang == 'en':
        for idx, doc in enumerate(indexes['en_docs']):
            doc_text = f"{doc['title']} {doc['body']}"
            score = fuzz.token_set_ratio(normalized_query, doc_text)
            fuzzy_scores[('en', idx)] = score
        
        if translated_query:
            for idx, doc in enumerate(indexes['bn_docs']):
                doc_text = f"{doc['title']} {doc['body']}"
                score = fuzz.token_set_ratio(translated_query, doc_text)
                fuzzy_scores[('bn', idx)] = score
    else:
        for idx, doc in enumerate(indexes['bn_docs']):
            doc_text = f"{doc['title']} {doc['body']}"
            score = fuzz.token_set_ratio(normalized_query, doc_text)
            fuzzy_scores[('bn', idx)] = score
        
        if translated_query:
            for idx, doc in enumerate(indexes['en_docs']):
                doc_text = f"{doc['title']} {doc['body']}"
                score = fuzz.token_set_ratio(translated_query, doc_text)
                fuzzy_scores[('en', idx)] = score
    
    # === Strategy 3: Semantic ===
    semantic_scores = {}
    query_embedding = embedding_model.encode(normalized_query)
    
    if detected_lang == 'en':
        en_texts = [f"{d['title']} {d['body']}" for d in indexes['en_docs']]
        if en_texts:
            en_embeddings = embedding_model.encode(en_texts)
            similarities = cosine_similarity([query_embedding], en_embeddings)[0]
            for idx, score in enumerate(similarities):
                semantic_scores[('en', idx)] = score * 100
        
        if translated_query:
            query_embedding_bn = embedding_model.encode(translated_query)
            bn_texts = [f"{d['title']} {d['body']}" for d in indexes['bn_docs']]
            if bn_texts:
                bn_embeddings = embedding_model.encode(bn_texts)
                similarities = cosine_similarity([query_embedding_bn], bn_embeddings)[0]
                for idx, score in enumerate(similarities):
                    semantic_scores[('bn', idx)] = score * 100
    else:
        bn_texts = [f"{d['title']} {d['body']}" for d in indexes['bn_docs']]
        if bn_texts:
            bn_embeddings = embedding_model.encode(bn_texts)
            similarities = cosine_similarity([query_embedding], bn_embeddings)[0]
            for idx, score in enumerate(similarities):
                semantic_scores[('bn', idx)] = score * 100
        
        if translated_query:
            query_embedding_en = embedding_model.encode(translated_query)
            en_texts = [f"{d['title']} {d['body']}" for d in indexes['en_docs']]
            if en_texts:
                en_embeddings = embedding_model.encode(en_texts)
                similarities = cosine_similarity([query_embedding_en], en_embeddings)[0]
                for idx, score in enumerate(similarities):
                    semantic_scores[('en', idx)] = score * 100
    
    # === Normalize scores to 0-1 range ===
    max_bm25 = max(bm25_scores.values()) if bm25_scores else 1
    max_fuzzy = max(fuzzy_scores.values()) if fuzzy_scores else 1
    max_semantic = max(semantic_scores.values()) if semantic_scores else 1
    
    normalized_bm25 = {k: v / max_bm25 for k, v in bm25_scores.items()}
    normalized_fuzzy = {k: v / max_fuzzy for k, v in fuzzy_scores.items()}
    normalized_semantic = {k: v / max_semantic for k, v in semantic_scores.items()}
    
    # === Weighted combination ===
    hybrid_scores = {}
    all_doc_ids = set(bm25_scores.keys()) | set(fuzzy_scores.keys()) | set(semantic_scores.keys())
    
    for doc_id in all_doc_ids:
        score = (
            weights['bm25'] * normalized_bm25.get(doc_id, 0) +
            weights['fuzzy'] * normalized_fuzzy.get(doc_id, 0) +
            weights['semantic'] * normalized_semantic.get(doc_id, 0)
        )
        hybrid_scores[doc_id] = score
    
    # === Sort and prepare results ===
    sorted_docs = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
    
    results = []
    for rank, (doc_id, score) in enumerate(sorted_docs[:10], 1):
        lang, idx = doc_id
        doc = indexes[f'{lang}_docs'][idx]
        
        result = {
            'rank': rank,
            'title': doc.get('title', '')[:80],
            'body': doc.get('body', '')[:150],
            'language': lang,
            'hybrid_score': float(score * 100),
            'bm25_score': float(normalized_bm25.get(doc_id, 0) * 100),
            'fuzzy_score': float(normalized_fuzzy.get(doc_id, 0) * 100),
            'semantic_score': float(normalized_semantic.get(doc_id, 0) * 100),
            'url': doc.get('url', ''),
        }
        results.append(result)
    
    return {
        'raw_query': query,
        'language': detected_lang,
        'normalized': normalized_query,
        'translated': translated_query if translated_query != normalized_query else None,
        'weights': weights,
        'results': results,
    }


def main():
    print("\n[*] Loading documents...")
    docs = load_documents()
    if not docs:
        print("[ERROR] No documents loaded")
        return 1
    
    en_count = sum(1 for d in docs if d.get('language') == 'en')
    bn_count = sum(1 for d in docs if d.get('language') == 'bn')
    print(f"[OK] {len(docs)} documents ({en_count} EN, {bn_count} BN)\n")
    
    print("[*] Building BM25 indexes...")
    indexes = build_indexes(docs)
    print("[OK] Indexes ready\n")
    
    print("[*] Loading embedding model (LaBSE)...")
    try:
        embedding_model = SentenceTransformer('sentence-transformers/LaBSE')
        print("[OK] Model loaded\n")
    except Exception as e:
        print(f"[ERROR] Could not load model: {e}")
        return 1
    
    print("[*] Initializing QueryProcessor (Module B)...")
    processor = QueryProcessor()
    print("[OK] Module B ready\n")
    
    # Test queries
    test_queries = [
        "Bangladesh politics",
        "cricket news",
        "education system",
        "dhaka economy",
        "energy crisis",
        "বাংলাদেশের রাজনীতি",
        "ক্রিকেট সংবাদ",
        "শিক্ষা ব্যবস্থা",
        "ঢাকার অর্থনীতি",
        "শক্তি সংকট",
    ]
    
    weights = {'bm25': 0.2, 'fuzzy': 0.1, 'semantic': 0.7}
    print(f"[*] Weights: BM25={weights['bm25']}, Fuzzy={weights['fuzzy']}, Semantic={weights['semantic']}\n")
    print(f"[*] Running {len(test_queries)} queries through hybrid search...\n")
    
    results_list = []
    for i, query in enumerate(test_queries, 1):
        print(f"[{i:2d}/10] {query[:40]:40s} ...", end=" ", flush=True)
        
        start = time.time()
        result = search_hybrid(docs, indexes, query, embedding_model, weights=weights, k=10)
        elapsed = (time.time() - start) * 1000
        
        result['execution_time_ms'] = elapsed
        results_list.append(result)
        
        print(f"{elapsed:.1f}ms")
    
    # Output to JSON
    json_path = "results/hybrid_results.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_list, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON saved to {json_path}")
    
    # Output to CSV
    csv_path = "results/hybrid_results.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Query', 'Lang', 'Translated', 'Rank-1 Title', 'Hybrid', 'BM25', 'Fuzzy', 'Semantic', 'Time(ms)'])
        
        for r in results_list:
            top = r['results'][0] if r['results'] else None
            if top:
                writer.writerow([
                    r['raw_query'],
                    r['language'],
                    r['translated'] or '-',
                    top['title'],
                    f"{top['hybrid_score']:.1f}%",
                    f"{top['bm25_score']:.1f}%",
                    f"{top['fuzzy_score']:.1f}%",
                    f"{top['semantic_score']:.1f}%",
                    f"{r['execution_time_ms']:.1f}",
                ])
    
    print(f"[OK] CSV saved to {csv_path}\n")
    
    # Print summary
    print("="*90)
    print("HYBRID SEARCH RESULTS SUMMARY (BM25 + Fuzzy + Semantic)")
    print("="*90 + "\n")
    
    for r in results_list:
        print(f"Query: {r['raw_query']} ({r['language'].upper()})")
        if r['translated']:
            print(f"  Translation: {r['translated']}")
        print(f"  Time: {r['execution_time_ms']:.1f}ms")
        print(f"  Top 5 Results:")
        
        for res in r['results'][:5]:
            rank = res.get('rank', '?')
            hybrid = res.get('hybrid_score', 0)
            print(f"    {rank}. [H:{hybrid:.1f}% B:{res['bm25_score']:.1f}% F:{res['fuzzy_score']:.1f}% S:{res['semantic_score']:.1f}%] {res['title']} ({res['language']})")
        
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
