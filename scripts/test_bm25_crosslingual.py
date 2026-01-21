"""
Module C - BM25 Cross-Lingual Test Suite
Tests BM25 search strategy on 30 test queries
Integrates Module B for query translation + cross-lingual search
Searches in BOTH English and Bangla documents
"""

import sys
import json
import time
import csv
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.bm25 import BM25Search
from src.query.processor import QueryProcessor
from src.query.translator import translate_bn_to_en, translate_en_to_bn


def load_documents(filepath: str = "notebooks/data/articles_with_ner.jsonl", limit: int = None) -> List[Dict]:
    """Load documents from JSONL."""
    docs = []
    print(f"📂 Loading documents from {filepath}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if line.strip():
                    docs.append(json.loads(line))
                    if limit and len(docs) >= limit:
                        break
        
        print(f"✅ Loaded {len(docs)} documents\n")
        
        # Count by language
        en_count = sum(1 for d in docs if d.get('language') == 'en')
        bn_count = sum(1 for d in docs if d.get('language') == 'bn')
        print(f"   English: {en_count}, Bangla: {bn_count}\n")
        
        return docs
    except Exception as e:
        print(f"❌ Error loading documents: {e}")
        return []


def load_test_queries(filepath: str = "data/test_queries.csv") -> List[Dict]:
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
        
        print(f"✅ Loaded {len(queries)} test queries")
        en = sum(1 for q in queries if q['language'] == 'en')
        bn = sum(1 for q in queries if q['language'] == 'bn')
        print(f"   English: {en}, Bangla: {bn}\n")
        
        return queries
    except Exception as e:
        print(f"❌ Error loading queries: {e}")
        return []


def search_crosslingual(bm25: BM25Search, query: str, query_lang: str, k: int = 10) -> List[Dict]:
    """
    Search in both languages using translation.
    
    Args:
        bm25: BM25Search instance
        query: Search query
        query_lang: Original query language ('en' or 'bn')
        k: Number of results to return
    
    Returns:
        List of result dictionaries with deduplication
    """
    all_results = []
    
    # Search in original language
    try:
        search_results = bm25.search(query, k=k*2)  # Get more to account for duplicate filtering
        for doc_id, score, doc in search_results:
            all_results.append({
                'doc_id': doc_id,
                'score': score,
                'title': doc.get('title', ''),
                'body_snippet': doc.get('body', '')[:100],
                'language': doc.get('language', '?'),
                'url': doc.get('url', ''),
                'search_lang': query_lang,
            })
    except Exception as e:
        print(f"  ⚠️  Error searching original language: {e}")
    
    # Translate query and search in other language
    try:
        if query_lang == 'en':
            # Translate English to Bangla
            translated_query = translate_en_to_bn(query)
        else:
            # Translate Bangla to English
            translated_query = translate_bn_to_en(query)
        
        if translated_query and translated_query != query:
            search_results = bm25.search(translated_query, k=k*2)
            for doc_id, score, doc in search_results:
                # Check if already in results (avoid duplicates)
                if not any(r['doc_id'] == doc_id for r in all_results):
                    all_results.append({
                        'doc_id': doc_id,
                        'score': score,
                        'title': doc.get('title', ''),
                        'body_snippet': doc.get('body', '')[:100],
                        'language': doc.get('language', '?'),
                        'url': doc.get('url', ''),
                        'search_lang': 'bn' if query_lang == 'en' else 'en',
                    })
    except Exception as e:
        print(f"  ⚠️  Error searching translated language: {e}")
    
    # Sort by score and return top k
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:k]


def test_bm25_crosslingual(bm25: BM25Search, queries: List[Dict]) -> Dict:
    """Test cross-lingual BM25 on all queries."""
    
    results = {
        'method': 'BM25 (Cross-Lingual)',
        'total_queries': len(queries),
        'successful': 0,
        'failed': 0,
        'total_time_ms': 0,
        'queries': [],
    }
    
    print("\n" + "="*70)
    print("TESTING BM25 (CROSS-LINGUAL)")
    print("="*70 + "\n")
    
    for i, q in enumerate(queries, 1):
        query = q['query']
        lang = q['language']
        
        try:
            # Run cross-lingual search
            start_time = time.time()
            search_results = search_crosslingual(bm25, query, lang, k=10)
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            
            # Format top 5 results
            formatted_results = []
            for rank, result in enumerate(search_results[:5], 1):
                formatted_results.append({
                    'rank': rank,
                    'title': result['title'][:60],
                    'language': result['language'],
                    'score': float(result['score']),
                    'search_lang': result['search_lang'],
                })
            
            query_result = {
                'query': query,
                'language': lang,
                'success': True,
                'time_ms': elapsed,
                'result_count': len(search_results),
                'results': formatted_results,
            }
            results['queries'].append(query_result)
            results['successful'] += 1
            results['total_time_ms'] += elapsed
            
            # Print progress
            lang_label = "EN" if lang == 'en' else "BN"
            result_summary = f"{len(search_results)} docs"
            print(f"[{i:2d}/30] ✅ {lang_label} | {query[:40]:40s} | {elapsed:6.1f}ms | {result_summary}")
            
        except Exception as e:
            query_result = {
                'query': query,
                'language': lang,
                'success': False,
                'error': str(e)[:100],
            }
            results['queries'].append(query_result)
            results['failed'] += 1
            
            print(f"[{i:2d}/30] ❌ {lang} | {query[:40]:40s} | ERROR: {str(e)[:30]}")
    
    # Calculate stats
    if results['successful'] > 0:
        results['avg_time_ms'] = results['total_time_ms'] / results['successful']
    else:
        results['avg_time_ms'] = 0
    
    return results


def print_results_summary(results: Dict):
    """Print test results summary."""
    
    print("\n\n" + "="*70)
    print("RESULTS SUMMARY - BM25 (CROSS-LINGUAL)")
    print("="*70 + "\n")
    
    print(f"Total Queries:     {results['total_queries']}")
    print(f"Successful:        {results['successful']} ✅")
    print(f"Failed:            {results['failed']} ❌")
    
    if results['total_queries'] > 0:
        print(f"Success Rate:      {results['successful']/results['total_queries']:.1%}")
    
    print(f"\nTotal Time:        {results['total_time_ms']:.1f}ms")
    print(f"Average Time/Query: {results['avg_time_ms']:.1f}ms")
    
    # Sample results
    print(f"\n" + "="*70)
    print("SAMPLE RESULTS (First 2 Successful Queries)")
    print("="*70 + "\n")
    
    successful_queries = [q for q in results['queries'] if q.get('success')]
    
    for q in successful_queries[:2]:
        print(f"📝 Query: {q['query']} ({q['language'].upper()})")
        print(f"   Time: {q['time_ms']:.1f}ms | Results: {q['result_count']}")
        print(f"   Top 5 Results:")
        for r in q.get('results', []):
            search_indicator = "🌐" if r['search_lang'] != q['language'] else "🔍"
            print(f"      {r['rank']}. [{r['score']:.3f}] {search_indicator} {r['title']}... ({r['language']})")
        print()
    
    # Statistics by language
    print(f"{"="*70}")
    print("STATISTICS BY LANGUAGE")
    print(f"{"="*70}\n")
    
    en_queries = [q for q in results['queries'] if q['language'] == 'en' and q.get('success')]
    bn_queries = [q for q in results['queries'] if q['language'] == 'bn' and q.get('success')]
    
    if en_queries:
        en_times = [q['time_ms'] for q in en_queries]
        en_results = [q['result_count'] for q in en_queries]
        print(f"English Queries:")
        print(f"  Count:        {len(en_queries)}")
        print(f"  Avg Time:     {sum(en_times)/len(en_times):.1f}ms")
        print(f"  Avg Results:  {sum(en_results)/len(en_results):.1f}")
        print(f"  Min/Max Time: {min(en_times):.1f}ms / {max(en_times):.1f}ms")
        print()
    
    if bn_queries:
        bn_times = [q['time_ms'] for q in bn_queries]
        bn_results = [q['result_count'] for q in bn_queries]
        print(f"Bangla Queries:")
        print(f"  Count:        {len(bn_queries)}")
        print(f"  Avg Time:     {sum(bn_times)/len(bn_times):.1f}ms")
        print(f"  Avg Results:  {sum(bn_results)/len(bn_results):.1f}")
        print(f"  Min/Max Time: {min(bn_times):.1f}ms / {max(bn_times):.1f}ms")


def save_results_json(results: Dict, filepath: str = "results/bm25_crosslingual_test_results.json"):
    """Save detailed results to JSON."""
    
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Results saved to {filepath}")
    except Exception as e:
        print(f"\n⚠️  Could not save results: {e}")


def main():
    """Main test runner."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*12 + "MODULE C - BM25 Cross-Lingual Test Suite" + " "*15 + "║")
    print("╚" + "="*68 + "╝\n")
    
    # Step 1: Load documents
    docs = load_documents(limit=None)  # Load ALL documents for better results
    if not docs:
        print("❌ Failed to load documents")
        return 1
    
    # Step 2: Load test queries
    queries = load_test_queries()
    if not queries:
        print("❌ Failed to load queries")
        return 1
    
    # Step 3: Initialize BM25
    print("Initializing BM25...")
    try:
        bm25 = BM25Search(docs)
        print(f"✅ BM25 Ready (indexed {len(docs)} documents)\n")
    except Exception as e:
        print(f"❌ Failed to initialize BM25: {e}")
        return 1
    
    # Step 4: Run tests
    results = test_bm25_crosslingual(bm25, queries)
    
    # Step 5: Print summary
    print_results_summary(results)
    
    # Step 6: Save results
    save_results_json(results)
    
    print("\n" + "="*70)
    print("✅ BM25 Cross-Lingual Test Complete!")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
