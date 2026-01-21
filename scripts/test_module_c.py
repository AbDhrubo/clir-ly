"""
Module C - Retrieval Models Testing & Comparison
Test all 4 retrieval methods on real queries
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.bm25 import BM25Search
from src.retrieval.fuzzy import FuzzySearch
from src.retrieval.semantic import SemanticSearch
from src.retrieval.hybrid import HybridSearch


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
        
        print(f"✅ Loaded {len(docs)} documents")
        
        # Count by language
        en_count = sum(1 for d in docs if d.get('language') == 'en')
        bn_count = sum(1 for d in docs if d.get('language') == 'bn')
        print(f"   English: {en_count}, Bangla: {bn_count}\n")
        
        return docs
    except Exception as e:
        print(f"❌ Error loading documents: {e}")
        return []


def test_single_method(method_name: str, search_obj, query: str, k: int = 10) -> Dict:
    """Test a single retrieval method."""
    try:
        start_time = time.time()
        results = search_obj.search(query, k=k)
        elapsed = time.time() - start_time
        
        return {
            'method': method_name,
            'query': query,
            'results': results,
            'elapsed_ms': elapsed * 1000,
            'count': len(results),
            'success': True,
        }
    except Exception as e:
        return {
            'method': method_name,
            'query': query,
            'results': [],
            'elapsed_ms': 0,
            'count': 0,
            'success': False,
            'error': str(e),
        }


def print_results(test_results: List[Dict], query: str):
    """Print results from all methods for a query."""
    print(f"\n{'='*70}")
    print(f"QUERY: {query}")
    print(f"{'='*70}")
    
    for result in test_results:
        method = result['method']
        elapsed = result['elapsed_ms']
        count = result['count']
        success = result['success']
        
        if success:
            print(f"\n✅ {method.upper()} ({elapsed:.1f}ms, {count} results)")
            print(f"   {'-'*66}")
            
            for i, doc in enumerate(result['results'][:5], 1):
                title = doc.get('title', 'N/A')[:50]
                score = doc.get('score', 0)
                lang = doc.get('language', '?')
                print(f"   {i}. [{score:.2f}] {title}... ({lang})")
        else:
            error = result.get('error', 'Unknown error')
            print(f"\n❌ {method.upper()} FAILED: {error}")


def compare_methods_summary(all_results: List[List[Dict]]):
    """Print comparison summary."""
    print(f"\n\n{'='*70}")
    print("COMPARISON SUMMARY")
    print(f"{'='*70}\n")
    
    methods = {}
    
    for query_results in all_results:
        for result in query_results:
            method = result['method']
            if method not in methods:
                methods[method] = {'total_time': 0, 'queries': 0, 'successes': 0}
            
            methods[method]['total_time'] += result['elapsed_ms']
            methods[method]['queries'] += 1
            if result['success']:
                methods[method]['successes'] += 1
    
    print(f"{'Method':<15} {'Queries':<10} {'Success':<10} {'Avg Time (ms)':<15}")
    print(f"{'-'*50}")
    
    for method, stats in sorted(methods.items()):
        avg_time = stats['total_time'] / stats['queries'] if stats['queries'] > 0 else 0
        success_rate = f"{stats['successes']}/{stats['queries']}"
        print(f"{method:<15} {success_rate:<10} {avg_time:<15.1f}")
    
    print()


def main():
    """Main test runner."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "MODULE C - Retrieval Models Comparison" + " "*15 + "║")
    print("╚" + "="*68 + "╝\n")
    
    # Step 1: Load documents
    docs = load_documents(limit=2000)  # Use 2000 for faster testing
    if not docs:
        print("❌ Failed to load documents")
        return 1
    
    # Step 2: Define test queries
    test_queries = [
        # English queries
        "Bangladesh politics",
        "cricket in Dhaka",
        "Bangladesh economy news",
        
        # Bangla queries
        "বাংলাদেশের রাজনীতি",
        "ঢাকায় ক্রিকেট",
        "বাংলাদেশের অর্থনীতি",
    ]
    
    # Step 3: Initialize retrieval methods
    print("Initializing retrieval methods...\n")
    
    try:
        print("1️⃣  BM25...")
        bm25 = BM25Search(docs)
        print("   ✅ Ready\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        bm25 = None
    
    try:
        print("2️⃣  Fuzzy...")
        fuzzy = FuzzySearch(docs)
        print("   ✅ Ready\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        fuzzy = None
    
    try:
        print("3️⃣  Semantic (this may take a minute)...")
        semantic = SemanticSearch(docs)
        print("   ✅ Ready\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        semantic = None
    
    try:
        print("4️⃣  Hybrid...")
        hybrid = HybridSearch(docs)
        print("   ✅ Ready\n")
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
        hybrid = None
    
    if not any([bm25, fuzzy, semantic, hybrid]):
        print("❌ No retrieval methods initialized")
        return 1
    
    # Step 4: Run tests
    print("\n" + "="*70)
    print("RUNNING TESTS")
    print("="*70)
    
    all_results = []
    
    for query in test_queries:
        query_results = []
        
        if bm25:
            query_results.append(test_single_method("BM25", bm25, query))
        if fuzzy:
            query_results.append(test_single_method("Fuzzy", fuzzy, query))
        if semantic:
            query_results.append(test_single_method("Semantic", semantic, query))
        if hybrid:
            query_results.append(test_single_method("Hybrid", hybrid, query))
        
        all_results.append(query_results)
        print_results(query_results, query)
    
    # Step 5: Print summary
    compare_methods_summary(all_results)
    
    print("✅ Testing complete!")
    print("\nNext steps:")
    print("  1. Review results above")
    print("  2. Note which methods are fastest")
    print("  3. Note which results are most relevant")
    print("  4. Based on this, we'll suggest optimal hybrid weights")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
