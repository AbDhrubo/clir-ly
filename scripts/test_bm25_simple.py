"""
BM25 CROSS-LINGUAL TEST - SIMPLE VERSION
Demonstrates cross-lingual retrieval: search in both EN/BN documents
Uses Module B (query translation)
"""

import sys
import json
import time
import csv
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.bm25 import BM25Search

# Try to import translation (Module B)
HAS_TRANSLATION = True
try:
    from src.query.translator import translate_bn_to_en, translate_en_to_bn
except ImportError:
    HAS_TRANSLATION = False
    def translate_bn_to_en(text): return None
    def translate_en_to_bn(text): return None


def load_documents(filepath="notebooks/data/articles_with_ner.jsonl", limit=None):
    """Load documents from JSONL."""
    docs = []
    print(f"Loading documents from {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if line.strip():
                    docs.append(json.loads(line))
                    if limit and len(docs) >= limit:
                        break
        
        print(f"[OK] Loaded {len(docs)} documents")
        
        en_count = sum(1 for d in docs if d.get('language') == 'en')
        bn_count = sum(1 for d in docs if d.get('language') == 'bn')
        print(f"     English: {en_count}, Bangla: {bn_count}\n")
        
        return docs
    except Exception as e:
        print(f"[ERROR] {e}")
        return []


def load_test_queries(filepath="data/test_queries.csv"):
    """Load test queries from CSV."""
    queries = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                queries.append({
                    'query': row['query'].strip(),
                    'language': row['language'].strip(),
                })
        
        print(f"[OK] Loaded {len(queries)} test queries")
        en = sum(1 for q in queries if q['language'] == 'en')
        bn = sum(1 for q in queries if q['language'] == 'bn')
        print(f"     English: {en}, Bangla: {bn}\n")
        
        return queries
    except Exception as e:
        print(f"[ERROR] {e}")
        return []


def search_crosslingual(bm25, query, query_lang, k=10):
    """Search in both languages."""
    all_results = []
    seen_doc_ids = set()
    
    # Search 1: Original language
    try:
        results = bm25.search(query, k=k*2)
        for doc_id, score, doc in results:
            all_results.append({
                'doc_id': doc_id,
                'score': score,
                'title': doc.get('title', '')[:70],
                'language': doc.get('language', '?'),
                'source': 'original',
            })
            seen_doc_ids.add(doc_id)
    except Exception as e:
        pass
    
    # Search 2: Translated language
    if HAS_TRANSLATION:
        try:
            if query_lang == 'en':
                translated = translate_en_to_bn(query)
            else:
                translated = translate_bn_to_en(query)
            
            if translated and translated != query:
                results = bm25.search(translated, k=k*2)
                for doc_id, score, doc in results:
                    if doc_id not in seen_doc_ids:
                        all_results.append({
                            'doc_id': doc_id,
                            'score': score,
                            'title': doc.get('title', '')[:70],
                            'language': doc.get('language', '?'),
                            'source': 'translated',
                        })
                        seen_doc_ids.add(doc_id)
        except Exception as e:
            pass
    
    # Sort and return top k
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:k]


def main():
    print("\n" + "="*70)
    print("BM25 CROSS-LINGUAL TEST")
    print("="*70 + "\n")
    
    # Load data
    docs = load_documents(limit=None)
    if not docs:
        print("[ERROR] Failed to load documents")
        return 1
    
    queries = load_test_queries()
    if not queries:
        print("[ERROR] Failed to load queries")
        return 1
    
    # Initialize BM25
    print("Initializing BM25...")
    try:
        bm25 = BM25Search(docs)
        print(f"[OK] BM25 ready with {len(docs)} documents\n")
    except Exception as e:
        print(f"[ERROR] {e}")
        return 1
    
    # Run tests
    print("TESTING (30 queries)")
    print("-" * 70 + "\n")
    
    total_time = 0
    successful = 0
    failed = 0
    
    for i, q in enumerate(queries, 1):
        query = q['query']
        lang = q['language']
        lang_label = "EN" if lang == 'en' else "BN"
        
        try:
            start = time.time()
            results = search_crosslingual(bm25, query, lang, k=10)
            elapsed = (time.time() - start) * 1000
            
            successful += 1
            total_time += elapsed
            
            status = "OK"
            result_count = len(results)
            
        except Exception as e:
            failed += 1
            elapsed = 0
            result_count = 0
            status = f"FAIL: {str(e)[:20]}"
        
        print(f"[{i:2d}/30] {lang_label} | {query[:40]:40s} | {elapsed:6.1f}ms | {result_count:2d} results | {status}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70 + "\n")
    
    print(f"Module B Translation: {'ENABLED' if HAS_TRANSLATION else 'DISABLED'}")
    print(f"Total Queries:  {len(queries)}")
    print(f"Successful:     {successful}")
    print(f"Failed:         {failed}")
    print(f"Success Rate:   {successful/len(queries):.1%}\n")
    
    print(f"Total Time:     {total_time:.1f}ms")
    if successful > 0:
        print(f"Avg Time/Query: {total_time/successful:.1f}ms")
    
    print("\n[OK] Test complete!\n")
    
    return 0


if __name__ == "__main__":
    exit(main())
