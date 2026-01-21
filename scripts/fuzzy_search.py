#!/usr/bin/env python3
"""
Module C - Fuzzy/Transliteration Search
Fuzzy matching for typos, transliteration, and phonetic matching
Single script: query → Module B → fuzzy cross-lingual search → JSON/CSV results
"""

import sys
import json
import csv
import time
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.processor import QueryProcessor

try:
    from fuzzywuzzy import fuzz
    from fuzzywuzzy import process
except ImportError:
    print("[ERROR] fuzzywuzzy not installed. Install with: pip install fuzzywuzzy python-Levenshtein")
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


def search_crosslingual(docs: List[Dict], query: str, query_lang: str, k: int = 10):
    """
    Full pipeline: raw query → Module B processing → fuzzy cross-lingual search
    
    Uses token-based fuzzy matching on title + body
    """
    processor = QueryProcessor()
    processed = processor.process(query)
    
    detected_lang = processed['language']
    normalized_query = processed['normalized']
    translated_query = processed['translated']
    
    en_results = []
    bn_results = []
    
    # Combine title + body for matching
    doc_texts = {}
    for i, doc in enumerate(docs):
        doc_texts[i] = f"{doc.get('title', '')} {doc.get('body', '')}"
    
    # Search 1: Original language
    if detected_lang == 'en':
        en_docs = {i: txt for i, doc in enumerate(docs) if doc.get('language') == 'en' 
                   for txt in [doc_texts[i]]}
        matches = process.extract(normalized_query, en_docs.values(), scorer=fuzz.token_set_ratio, limit=20)
        
        for rank, (match_text, score) in enumerate(matches, 1):
            for doc_id, txt in en_docs.items():
                if txt == match_text:
                    doc = docs[doc_id]
                    en_results.append({
                        'rank': rank,
                        'title': doc.get('title', '')[:80],
                        'body': doc.get('body', '')[:150],
                        'language': 'en',
                        'score': float(score),
                        'url': doc.get('url', ''),
                    })
                    break
        
        # Search 2: Translated to Bangla
        if translated_query:
            bn_docs = {i: txt for i, doc in enumerate(docs) if doc.get('language') == 'bn' 
                       for txt in [doc_texts[i]]}
            matches = process.extract(translated_query, bn_docs.values(), scorer=fuzz.token_set_ratio, limit=20)
            
            for rank, (match_text, score) in enumerate(matches, 1):
                for doc_id, txt in bn_docs.items():
                    if txt == match_text:
                        doc = docs[doc_id]
                        bn_results.append({
                            'rank': rank,
                            'title': doc.get('title', '')[:80],
                            'body': doc.get('body', '')[:150],
                            'language': 'bn',
                            'score': float(score),
                            'url': doc.get('url', ''),
                        })
                        break
    else:
        # Bangla query
        bn_docs = {i: txt for i, doc in enumerate(docs) if doc.get('language') == 'bn' 
                   for txt in [doc_texts[i]]}
        matches = process.extract(normalized_query, bn_docs.values(), scorer=fuzz.token_set_ratio, limit=20)
        
        for rank, (match_text, score) in enumerate(matches, 1):
            for doc_id, txt in bn_docs.items():
                if txt == match_text:
                    doc = docs[doc_id]
                    bn_results.append({
                        'rank': rank,
                        'title': doc.get('title', '')[:80],
                        'body': doc.get('body', '')[:150],
                        'language': 'bn',
                        'score': float(score),
                        'url': doc.get('url', ''),
                    })
                    break
        
        # Search 2: Translated to English
        if translated_query:
            en_docs = {i: txt for i, doc in enumerate(docs) if doc.get('language') == 'en' 
                       for txt in [doc_texts[i]]}
            matches = process.extract(translated_query, en_docs.values(), scorer=fuzz.token_set_ratio, limit=20)
            
            for rank, (match_text, score) in enumerate(matches, 1):
                for doc_id, txt in en_docs.items():
                    if txt == match_text:
                        doc = docs[doc_id]
                        en_results.append({
                            'rank': rank,
                            'title': doc.get('title', '')[:80],
                            'body': doc.get('body', '')[:150],
                            'language': 'en',
                            'score': float(score),
                            'url': doc.get('url', ''),
                        })
                        break
    
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
    print("\n[*] Loading documents...")
    docs = load_documents()
    if not docs:
        print("[ERROR] No documents loaded")
        return 1
    
    en_count = sum(1 for d in docs if d.get('language') == 'en')
    bn_count = sum(1 for d in docs if d.get('language') == 'bn')
    print(f"[OK] {len(docs)} documents ({en_count} EN, {bn_count} BN)\n")
    
    print("[*] Initializing QueryProcessor (Module B)...")
    processor = QueryProcessor()
    print("[OK] Module B ready\n")
    
    # Load queries from CSV
    test_queries = []
    try:
        with open('data/test_queries.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_queries.append(row['query'])
        print(f"[*] Loaded {len(test_queries)} queries from data/test_queries.csv\n")
    except Exception as e:
        print(f"[ERROR] Could not load test_queries.csv: {e}")
        return 1
    
    print(f"[*] Running {len(test_queries)} queries through Module B + Fuzzy...\n")
    
    results_list = []
    for i, query in enumerate(test_queries, 1):
        print(f"[{i:2d}/{len(test_queries)}] {query[:40]:40s} ...", end=" ", flush=True)
        
        start = time.time()
        result = search_crosslingual(docs, query, query[0], k=10)
        elapsed = (time.time() - start) * 1000
        
        result['execution_time_ms'] = elapsed
        results_list.append(result)
        
        print(f"{elapsed:.1f}ms")
    
    # Output to JSON
    json_path = "results/fuzzy_results.json"
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_list, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] JSON saved to {json_path}")
    
    # Output to CSV
    csv_path = "results/fuzzy_results.csv"
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
                f"{score_en:.3f}",
                top_bn,
                f"{score_bn:.3f}",
                f"{r['execution_time_ms']:.1f}",
            ])
    
    print(f"[OK] CSV saved to {csv_path}\n")
    
    # Print summary
    print("="*70)
    print("FUZZY SEARCH RESULTS SUMMARY")
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
