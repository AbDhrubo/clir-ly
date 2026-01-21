"""
Module C - BM25 Cross-Lingual Test Suite
SIMPLIFIED VERSION - Works locally, shows cross-lingual structure
Tests BM25 search strategy on 30 test queries
Integrates Module B for query translation
Searches in BOTH English and Bangla documents

For full test with all features, run on Colab:
    !pip install -q transformers sentence-transformers
    !python scripts/test_bm25_crosslingual.py
"""

import sys
import json
import time
import csv
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.bm25 import BM25Search

# Import translation functions from Module B
HAS_TRANSLATION = True
try:
    from src.query.translator import translate_bn_to_en, translate_en_to_bn
except ImportError:
    HAS_TRANSLATION = False
    
    def translate_bn_to_en(text):
        return None
    
    def translate_en_to_bn(text):
        return None


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
    Search in both languages using Module B translation.
    
    Returns list of results with language info.
    Each result includes:
    - doc_id, title, language, score
    - search_lang: which language query was searched in
    - source: 'original' or 'translated'
    """
    all_results = []
    seen_doc_ids = set()
    
    # STEP 1: Search in original language
    print(f"  🔍 Searching in {query_lang.upper()} corpus...", end=" ")
    try:
        search_results = bm25.search(query, k=k*2)
        original_count = len(search_results)
        
        for doc_id, score, doc in search_results:
            all_results.append({
                'doc_id': doc_id,
                'score': score,
                'title': doc.get('title', '')[:70],
                'language': doc.get('language', '?'),
                'url': doc.get('url', ''),
                'source': 'original',
            })
            seen_doc_ids.add(doc_id)
        
        print(f"✅ {original_count} results")
    except Exception as e:
        print(f"❌ {str(e)[:50]}")
        original_count = 0
    
    # STEP 2: Translate and search in other language
    other_lang = 'bn' if query_lang == 'en' else 'en'
    
    if HAS_TRANSLATION:
        try:
            print(f"  🌐 Translating to {other_lang.upper()}...", end=" ")
            
            if query_lang == 'en':
                translated_query = translate_en_to_bn(query)
            else:
                translated_query = translate_bn_to_en(query)
            
            if translated_query and translated_query != query:
                print(f"✅ '{translated_query}'")
                print(f"  🔍 Searching translated in {other_lang.upper()} corpus...", end=" ")
                
                search_results = bm25.search(translated_query, k=k*2)
                translated_count = 0
                
                for doc_id, score, doc in search_results:
                    if doc_id not in seen_doc_ids:
                        all_results.append({
                            'doc_id': doc_id,
                            'score': score,
                            'title': doc.get('title', '')[:70],
                            'language': doc.get('language', '?'),
                            'url': doc.get('url', ''),
                            'source': 'translated',
                        })
                        seen_doc_ids.add(doc_id)
                        translated_count += 1
                
                print(f"✅ {translated_count} new results")
            else:
                print(f"❌ Translation same as original")
        
        except Exception as e:
            print(f"❌ {str(e)[:50]}")
    else:
        print(f"  ⚠️  Translation not available (Module B models not loaded)")
    
    # STEP 3: Sort by score and return top k
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return all_results[:k]


def test_bm25_crosslingual(bm25: BM25Search, queries: List[Dict]) -> Dict:
    """Test cross-lingual BM25 on all queries."""
    
    results = {
        'method': 'BM25 (Cross-Lingual)',
        'module_b_enabled': HAS_TRANSLATION,
        'total_queries': len(queries),
        'successful': 0,
        'failed': 0,
        'total_time_ms': 0,
        'queries': [],
    }
    
    print("\n" + "="*72)
    print("TESTING BM25 (CROSS-LINGUAL)")
    print("="*72 + "\n")
    
    for i, q in enumerate(queries, 1):
        query = q['query']
        lang = q['language']
        
        try:
            # Run cross-lingual search with timing
            start_time = time.time()
            search_results = search_crosslingual(bm25, query, lang, k=10)
            elapsed = (time.time() - start_time) * 1000  # Convert to ms
            
            # Format top 5 results
            formatted_results = []
            for rank, result in enumerate(search_results[:5], 1):
                source_icon = "🔍" if result['source'] == 'original' else "🌐"
                formatted_results.append({
                    'rank': rank,
                    'title': result['title'],
                    'language': result['language'],
                    'score': float(result['score']),
                    'source': result['source'],
                    'icon': source_icon,
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
            
            # Print results summary
            print(f"  ⏱️  Time: {elapsed:.1f}ms")
            print(f"  📊 Total Results: {len(search_results)}")
            
            original_results = sum(1 for r in search_results if r['source'] == 'original')
            translated_results = len(search_results) - original_results
            
            print(f"     - From {lang.upper()}: {original_results} results")
            print(f"     - From {'BN' if lang == 'en' else 'EN'} (translated): {translated_results} results")
            
            # Show top results
            print(f"  🏆 Top 5:")
            for r in formatted_results:
                print(f"     {r['icon']} {r['rank']}. [{r['score']:.3f}] {r['title']} ({r['language']})")
            
            print(f"  ✅ Success")
            
        except Exception as e:
            query_result = {
                'query': query,
                'language': lang,
                'success': False,
                'error': str(e)[:100],
            }
            results['queries'].append(query_result)
            results['failed'] += 1
            
            print(f"  ❌ ERROR: {str(e)[:60]}")
    
    # Calculate stats
    if results['successful'] > 0:
        results['avg_time_ms'] = results['total_time_ms'] / results['successful']
    else:
        results['avg_time_ms'] = 0
    
    return results


def print_results_summary(results: Dict):
    """Print test results summary."""
    
    print("\n\n" + "="*72)
    print("RESULTS SUMMARY - BM25 (CROSS-LINGUAL)")
    print("="*72 + "\n")
    
    print(f"📋 Configuration:")
    print(f"   Module B Translation: {'✅ ENABLED' if results['module_b_enabled'] else '❌ DISABLED'}")
    print(f"\n📊 Results:")
    print(f"   Total Queries:     {results['total_queries']}")
    print(f"   Successful:        {results['successful']} ✅")
    print(f"   Failed:            {results['failed']} ❌")
    
    if results['total_queries'] > 0:
        print(f"   Success Rate:      {results['successful']/results['total_queries']:.1%}")
    
    print(f"\n⏱️  Performance:")
    print(f"   Total Time:        {results['total_time_ms']:.1f}ms")
    print(f"   Average/Query:     {results['avg_time_ms']:.1f}ms")
    
    # Results by language
    print(f"\n🌍 Results by Query Language:")
    print(f"{"="*72}\n")
    
    en_queries = [q for q in results['queries'] if q['language'] == 'en' and q.get('success')]
    bn_queries = [q for q in results['queries'] if q['language'] == 'bn' and q.get('success')]
    
    if en_queries:
        en_times = [q['time_ms'] for q in en_queries]
        en_results = [q['result_count'] for q in en_queries]
        print(f"English Queries (EN):")
        print(f"  Count:          {len(en_queries)}/15")
        print(f"  Avg Time:       {sum(en_times)/len(en_times):.1f}ms")
        print(f"  Avg Results:    {sum(en_results)/len(en_results):.1f}")
        print(f"  Min/Max Time:   {min(en_times):.1f}ms / {max(en_times):.1f}ms")
        print()
    
    if bn_queries:
        bn_times = [q['time_ms'] for q in bn_queries]
        bn_results = [q['result_count'] for q in bn_queries]
        print(f"Bangla Queries (BN):")
        print(f"  Count:          {len(bn_queries)}/15")
        print(f"  Avg Time:       {sum(bn_times)/len(bn_times):.1f}ms")
        print(f"  Avg Results:    {sum(bn_results)/len(bn_results):.1f}")
        print(f"  Min/Max Time:   {min(bn_times):.1f}ms / {max(bn_times):.1f}ms")


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
    print("+=" + "="*70 + "=+")
    print("|" + " "*12 + "MODULE C - BM25 Cross-Lingual Test Suite" + " "*17 + "|")
    print("==" + "="*70 + "==\n")
    
    print("ℹ️  This test demonstrates cross-lingual retrieval.")
    print("    Each query is searched in BOTH English and Bangla documents.\n")
    
    # Step 1: Load documents
    docs = load_documents(limit=None)
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
    
    print("\n" + "="*72)
    print("✅ BM25 Cross-Lingual Test Complete!")
    print("="*72)
    print("\n📚 Legend:")
    print("   🔍 = Result from original language search")
    print("   🌐 = Result from translated language search (cross-lingual)")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
