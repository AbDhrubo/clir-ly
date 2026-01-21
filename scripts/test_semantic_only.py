"""
Module C - Semantic Only Test Suite
Test Semantic/Embeddings retrieval on 30 test queries
"""

import sys
import json
import time
import csv
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.semantic import SemanticSearch


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


def test_semantic(semantic: SemanticSearch, queries: List[Dict], model_name: str) -> Dict:
    """Test Semantic on all queries."""
    
    results = {
        'method': 'Semantic',
        'model': model_name,
        'total_queries': len(queries),
        'successful': 0,
        'failed': 0,
        'total_time_ms': 0,
        'queries': [],
    }
    
    print("\n" + "="*70)
    print(f"TESTING SEMANTIC ({model_name})")
    print("="*70 + "\n")
    
    for i, q in enumerate(queries, 1):
        query = q['query']
        lang = q['language']
        
        try:
            start_time = time.time()
            search_results = semantic.search(query, k=10)
            elapsed = (time.time() - start_time) * 1000
            
            formatted_results = []
            for rank, result in enumerate(search_results[:5], 1):
                formatted_results.append({
                    'rank': rank,
                    'title': result.get('title', 'N/A')[:50],
                    'language': result.get('language', '?'),
                    'score': float(result.get('score', 0)),
                })
            
            query_result = {
                'query': query,
                'language': lang,
                'success': True,
                'time_ms': elapsed,
                'results': formatted_results,
            }
            results['queries'].append(query_result)
            results['successful'] += 1
            results['total_time_ms'] += elapsed
            
            print(f"[{i:2d}/30] ✅ {lang.upper():2s} | {query[:40]:40s} | {elapsed:6.1f}ms | {len(search_results)} docs")
            
        except Exception as e:
            query_result = {
                'query': query,
                'language': lang,
                'success': False,
                'error': str(e),
            }
            results['queries'].append(query_result)
            results['failed'] += 1
            
            print(f"[{i:2d}/30] ❌ {lang.upper():2s} | {query[:40]:40s} | ERROR: {str(e)[:30]}")
    
    if results['successful'] > 0:
        results['avg_time_ms'] = results['total_time_ms'] / results['successful']
    else:
        results['avg_time_ms'] = 0
    
    return results


def print_results_summary(results: Dict):
    """Print test results summary."""
    
    print("\n\n" + "="*70)
    print(f"RESULTS SUMMARY - SEMANTIC ({results['model']})")
    print("="*70 + "\n")
    
    print(f"Total Queries:     {results['total_queries']}")
    print(f"Successful:        {results['successful']} ✅")
    print(f"Failed:            {results['failed']} ❌")
    print(f"Success Rate:      {results['successful']/results['total_queries']:.1%}")
    print(f"\nTotal Time:        {results['total_time_ms']:.1f}ms")
    print(f"Average Time/Query: {results['avg_time_ms']:.1f}ms")
    
    print(f"\n" + "="*70)
    print("SAMPLE RESULTS (First 3 Successful Queries)")
    print("="*70 + "\n")
    
    successful_queries = [q for q in results['queries'] if q.get('success')]
    
    for q in successful_queries[:3]:
        print(f"📝 Query: {q['query']} ({q['language'].upper()})")
        print(f"   Time: {q['time_ms']:.1f}ms")
        print(f"   Top 5 Results:")
        for r in q.get('results', []):
            print(f"      {r['rank']}. [{r['score']:.3f}] {r['title']}... ({r['language']})")
        print()
    
    print(f"{"="*70}")
    print("STATISTICS BY LANGUAGE")
    print(f"{"="*70}\n")
    
    en_queries = [q for q in results['queries'] if q['language'] == 'en' and q.get('success')]
    bn_queries = [q for q in results['queries'] if q['language'] == 'bn' and q.get('success')]
    
    if en_queries:
        en_times = [q['time_ms'] for q in en_queries]
        print(f"English Queries:")
        print(f"  Count:   {len(en_queries)}")
        print(f"  Avg Time: {sum(en_times)/len(en_times):.1f}ms")
        print()
    
    if bn_queries:
        bn_times = [q['time_ms'] for q in bn_queries]
        print(f"Bangla Queries:")
        print(f"  Count:   {len(bn_queries)}")
        print(f"  Avg Time: {sum(bn_times)/len(bn_times):.1f}ms")


def save_results_json(results: Dict, filepath: str = "results/semantic_test_results.json"):
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
    print("║" + " "*17 + "MODULE C - Semantic Test Suite" + " "*20 + "║")
    print("╚" + "="*68 + "╝\n")
    
    docs = load_documents(limit=2000)
    if not docs:
        print("❌ Failed to load documents")
        return 1
    
    queries = load_test_queries()
    if not queries:
        print("❌ Failed to load queries")
        return 1
    
    model_name = 'sentence-transformers/LaBSE'
    print(f"Initializing Semantic (model: {model_name})...")
    try:
        semantic = SemanticSearch(docs, model_name=model_name)
        print("✅ Semantic Ready\n")
    except Exception as e:
        print(f"❌ Failed to initialize Semantic: {e}")
        return 1
    
    results = test_semantic(semantic, queries, model_name)
    print_results_summary(results)
    save_results_json(results)
    
    print("\n" + "="*70)
    print("✅ Semantic Test Complete!")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
