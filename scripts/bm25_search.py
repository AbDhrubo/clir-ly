#!/usr/bin/env python3
"""
Module C - BM25 Search with Module B Integration
Single script: query → Module B (detection/translation) → BM25 cross-lingual search → JSON/CSV results
"""

import sys
import json
import csv
import time
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.bm25 import BM25Search
from src.query.processor import QueryProcessor


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


def search_crosslingual(bm25: BM25Search, processor: QueryProcessor, raw_query: str):
    """
    Full pipeline: raw query → Module B processing → cross-lingual BM25 search
    
    Returns:
    {
        'raw_query': original input,
        'language': detected language,
        'normalized': cleaned query,
        'translated': translation to other language,
        'en_results': results from English search,
        'bn_results': results from Bangla search,
        'combined_results': merged top 10 results
    }
    """
    
    # STEP 1: Module B - Process query (detection, normalization, translation)
    processed = processor.process(raw_query)
    
    detected_lang = processed['language']
    normalized_query = processed['normalized']
    translated_query = processed['translated']
    
    # STEP 2: BM25 Search - Original language
    en_results = []
    bn_results = []
    
    if detected_lang == 'en':
        # English query on English docs
        en_search = bm25.search(normalized_query, k=20)
        for doc_id, score, doc in en_search:
            if doc.get('language') == 'en':
                en_results.append({
                    'title': doc.get('title', '')[:80],
                    'body': doc.get('body', '')[:150],
                    'language': 'en',
                    'score': float(score),
                    'url': doc.get('url', ''),
                })
        
        # Bangla translation on Bangla docs
        if translated_query and translated_query != normalized_query:
            bn_search = bm25.search(translated_query, k=20)
            for doc_id, score, doc in bn_search:
                if doc.get('language') == 'bn':
                    bn_results.append({
                        'title': doc.get('title', '')[:80],
                        'body': doc.get('body', '')[:150],
                        'language': 'bn',
                        'score': float(score),
                        'url': doc.get('url', ''),
                    })
    else:
        # Bangla query on Bangla docs
        bn_search = bm25.search(normalized_query, k=20)
        for doc_id, score, doc in bn_search:
            if doc.get('language') == 'bn':
                bn_results.append({
                    'title': doc.get('title', '')[:80],
                    'body': doc.get('body', '')[:150],
                    'language': 'bn',
                    'score': float(score),
                    'url': doc.get('url', ''),
                })
        
        # English translation on English docs
        if translated_query and translated_query != normalized_query:
            en_search = bm25.search(translated_query, k=20)
            for doc_id, score, doc in en_search:
                if doc.get('language') == 'en':
                    en_results.append({
                        'title': doc.get('title', '')[:80],
                        'body': doc.get('body', '')[:150],
                        'language': 'en',
                        'score': float(score),
                        'url': doc.get('url', ''),
                    })
    
    # STEP 3: Merge results (interleave EN and BN by score)
    combined = []
    en_idx = bn_idx = 0
    
    while len(combined) < 10 and (en_idx < len(en_results) or bn_idx < len(bn_results)):
        if en_idx < len(en_results) and bn_idx < len(bn_results):
            if en_results[en_idx]['score'] >= bn_results[bn_idx]['score']:
                combined.append(en_results[en_idx])
                en_idx += 1
            else:
                combined.append(bn_results[bn_idx])
                bn_idx += 1
        elif en_idx < len(en_results):
            combined.append(en_results[en_idx])
            en_idx += 1
        else:
            combined.append(bn_results[bn_idx])
            bn_idx += 1
    
    return {
        'raw_query': raw_query,
        'language': detected_lang,
        'normalized': normalized_query,
        'translated': translated_query if translated_query != normalized_query else None,
        'en_results': en_results[:5],
        'bn_results': bn_results[:5],
        'combined_top10': combined[:10],
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
    
    print("[*] Initializing BM25...")
    bm25 = BM25Search(docs)
    print("[OK] BM25 indexed\n")
    
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
    
    print(f"[*] Running {len(test_queries)} queries through Module B + BM25...\n")
    
    results_list = []
    for i, query in enumerate(test_queries, 1):
        print(f"[{i:2d}/10] {query[:40]:40s} ...", end=" ", flush=True)
        
        start = time.time()
        result = search_crosslingual(bm25, processor, query)
        elapsed = (time.time() - start) * 1000
        
        result['execution_time_ms'] = elapsed
        results_list.append(result)
        
        print(f"{elapsed:.1f}ms")
    
    # Output to JSON
    json_path = "results/bm25_results.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_list, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON saved to {json_path}")
    
    # Output to CSV
    csv_path = "results/bm25_results.csv"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Query', 'Language', 'Normalized', 'Translated', 'Top Result (EN)', 'Score', 'Top Result (BN)', 'Score', 'Time(ms)'])
        
        for r in results_list:
            top_en = r['en_results'][0]['title'] if r['en_results'] else '-'
            score_en = r['en_results'][0]['score'] if r['en_results'] else 0
            top_bn = r['bn_results'][0]['title'] if r['bn_results'] else '-'
            score_bn = r['bn_results'][0]['score'] if r['bn_results'] else 0
            
            writer.writerow([
                r['raw_query'],
                r['language'],
                r['normalized'],
                r['translated'] or '-',
                top_en,
                f"{score_en:.3f}",
                top_bn,
                f"{score_bn:.3f}",
                f"{r['execution_time_ms']:.1f}",
            ])
    
    print(f"[OK] CSV saved to {csv_path}\n")
    
    # Print summary
    print("="*70)
    print("RESULTS SUMMARY")
    print("="*70 + "\n")
    
    for r in results_list:
        print(f"Query: {r['raw_query']} ({r['language'].upper()})")
        if r['translated']:
            print(f"  Module B Translation: {r['translated']}")
        print(f"  Time: {r['execution_time_ms']:.1f}ms")
        print(f"  Top 10 Results:")
        
        for rank, res in enumerate(r['combined_top10'][:5], 1):
            print(f"    {rank}. [{res['score']:.3f}] {res['title']} ({res['language']})")
        
        print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
