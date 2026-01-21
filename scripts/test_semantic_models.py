"""
Module C - Semantic Model Comparison & Accuracy Testing
Compare different semantic models and test accuracy on labeled queries
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.semantic import SemanticSearch


# Available semantic models to test
SEMANTIC_MODELS = {
    'labse': {
        'name': 'sentence-transformers/LaBSE',
        'description': 'Best for multilingual, especially Bangla-English',
        'speed': 'Medium',
        'languages': '100+',
    },
    'xlm-r': {
        'name': 'sentence-transformers/xlm-r-large-en-ko-chinese-simplied-de-fr',
        'description': 'XLM-RoBERTa - slower but very accurate multilingual',
        'speed': 'Slow',
        'languages': '100+',
    },
    'mbert': {
        'name': 'sentence-transformers/mBERT-base-multilingual-cased',
        'description': 'Multilingual BERT - fast but older',
        'speed': 'Fast',
        'languages': '100+',
    },
    'paraphrase': {
        'name': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
        'description': 'Paraphrase model - good for semantic similarity',
        'speed': 'Fast',
        'languages': '50+',
    },
}


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
        return docs
    except Exception as e:
        print(f"❌ Error loading documents: {e}")
        return []


def test_semantic_model(model_key: str, docs: List[Dict], test_queries: List[str]) -> Dict:
    """Test a single semantic model."""
    
    model_info = SEMANTIC_MODELS[model_key]
    model_name = model_info['name']
    
    print(f"\n{'='*70}")
    print(f"Testing Model: {model_key.upper()}")
    print(f"Model Name: {model_name}")
    print(f"Description: {model_info['description']}")
    print(f"{'='*70}\n")
    
    results = {
        'model_key': model_key,
        'model_name': model_name,
        'queries': [],
        'total_time': 0,
        'avg_time': 0,
    }
    
    try:
        # Initialize semantic search with this model
        print(f"🔄 Initializing {model_key}...")
        semantic = SemanticSearch(docs, model_name=model_name)
        
        # Test each query
        for query in test_queries:
            print(f"\n  🔍 Query: {query}")
            
            try:
                start_time = time.time()
                search_results = semantic.search(query, k=10)
                elapsed = time.time() - start_time
                
                results['total_time'] += elapsed
                
                # Format results
                formatted = []
                for i, result in enumerate(search_results[:5], 1):
                    formatted.append({
                        'rank': i,
                        'title': result.get('title', 'N/A')[:50],
                        'language': result.get('language', '?'),
                        'score': float(result.get('score', 0)),
                    })
                
                query_result = {
                    'query': query,
                    'time_ms': elapsed * 1000,
                    'results': formatted,
                    'success': True,
                }
                results['queries'].append(query_result)
                
                print(f"     ✅ OK ({elapsed*1000:.1f}ms)")
                for r in formatted[:3]:
                    print(f"        {r['rank']}. [{r['score']:.3f}] {r['title']}... ({r['language']})")
                    
            except Exception as e:
                print(f"     ❌ Error: {e}")
                results['queries'].append({
                    'query': query,
                    'success': False,
                    'error': str(e),
                })
        
        # Calculate averages
        successful = [q for q in results['queries'] if q.get('success')]
        if successful:
            results['avg_time'] = results['total_time'] / len(successful)
            results['success_rate'] = len(successful) / len(test_queries)
        
        return results
        
    except Exception as e:
        print(f"❌ Failed to initialize model: {e}")
        return {
            'model_key': model_key,
            'model_name': model_name,
            'error': str(e),
            'success': False,
        }


def print_comparison(all_results: List[Dict]):
    """Print comparison of all models."""
    
    print(f"\n\n{'='*70}")
    print("MODEL COMPARISON SUMMARY")
    print(f"{'='*70}\n")
    
    print(f"{'Model':<20} {'Status':<10} {'Avg Time':<12} {'Success':<10}")
    print(f"{'-'*52}")
    
    for result in all_results:
        if result.get('success') is False:
            print(f"{result['model_key']:<20} {'FAILED':<10}")
        else:
            status = "✅ OK"
            avg_time = result.get('avg_time', 0)
            success_rate = f"{result.get('success_rate', 0):.0%}"
            print(f"{result['model_key']:<20} {status:<10} {avg_time:.1f}ms{'':<6} {success_rate:<10}")


def test_accuracy_manual():
    """
    Guide for manual accuracy testing
    """
    print(f"\n{'='*70}")
    print("ACCURACY TESTING - HOW TO DO IT")
    print(f"{'='*70}\n")
    
    print("""
Step 1: Create a labeled dataset
  - Pick 10-20 test queries (mix of English and Bangla)
  - For each query, manually mark which documents are relevant
  - Save as CSV: query,doc_url,relevant (yes/no)
  
Step 2: Run searches with each model
  - For each query, run search with each semantic model
  - Compare top-10 results with your labels
  
Step 3: Calculate metrics
  - Precision@10: How many of top-10 are relevant?
  - Recall@50: Of all relevant docs, how many did we find?
  - nDCG@10: Ranking quality (higher ranked = better)
  - MRR: Mean Reciprocal Rank (how far to first relevant?)
  
Step 4: Choose best model based on metrics

METRICS FORMULAS:
  • Precision@10 = (relevant docs in top-10) / 10
  • Recall@50 = (relevant docs retrieved) / (total relevant docs)
  • nDCG@10 = Sum(relevance_i / log2(rank_i + 1)) for i=1 to 10
  • MRR = 1 / rank_of_first_relevant_doc

TARGET VALUES:
  • Precision@10 >= 0.6  (at least 6 relevant in top-10)
  • Recall@50 >= 0.5     (find at least 50% of relevant docs)
  • nDCG@10 >= 0.5       (good ranking quality)
  • MRR >= 0.4           (first relevant in top 2-3)
    """)


def main():
    """Main test runner."""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*12 + "MODULE C - Semantic Models Comparison & Accuracy" + " "*8 + "║")
    print("╚" + "="*68 + "╝\n")
    
    # Load documents
    docs = load_documents(limit=1000)  # Use 1000 for faster testing
    if not docs:
        print("❌ Failed to load documents")
        return 1
    
    # Define test queries
    test_queries = [
        "Bangladesh politics",
        "বাংলাদেশের রাজনীতি",
        "cricket",
        "ক্রিকেট",
    ]
    
    print("\n" + "="*70)
    print("AVAILABLE MODELS")
    print("="*70 + "\n")
    
    for key, model in SEMANTIC_MODELS.items():
        print(f"{key.upper()}: {model['name']}")
        print(f"  Description: {model['description']}")
        print(f"  Speed: {model['speed']}, Languages: {model['languages']}\n")
    
    # Test models
    print("\n" + "="*70)
    print("TESTING MODELS")
    print("="*70)
    
    all_results = []
    models_to_test = ['labse', 'mbert', 'paraphrase']  # Skip xlm-r (very slow)
    
    for model_key in models_to_test:
        result = test_semantic_model(model_key, docs, test_queries)
        all_results.append(result)
    
    # Print comparison
    print_comparison(all_results)
    
    # Print accuracy testing guide
    test_accuracy_manual()
    
    print("\n✅ Testing complete!\n")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
