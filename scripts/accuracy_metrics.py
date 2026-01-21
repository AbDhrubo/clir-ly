"""
Module C - Accuracy Metrics Calculator
Compute Precision@10, Recall@50, nDCG@10, MRR
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Tuple
import math

sys.path.insert(0, str(Path(__file__).parent.parent))


class AccuracyMetrics:
    """Calculate IR evaluation metrics."""
    
    @staticmethod
    def precision_at_k(results: List[Dict], relevant_docs: List[str], k: int = 10) -> float:
        """
        Precision@k: How many of top-k results are relevant?
        
        Formula: (# relevant docs in top-k) / k
        
        Example:
            Top 10 results: [A(relevant), B(irrelevant), C(relevant), D(relevant), ...]
            If 6 are relevant: Precision@10 = 6/10 = 0.6
        """
        if k == 0:
            return 0.0
        
        relevant_count = 0
        for i, result in enumerate(results[:k]):
            doc_id = result.get('url') or result.get('title')
            if doc_id in relevant_docs:
                relevant_count += 1
        
        return relevant_count / k
    
    
    @staticmethod
    def recall_at_k(results: List[Dict], relevant_docs: List[str], k: int = 50) -> float:
        """
        Recall@k: Of all relevant docs, how many did we find?
        
        Formula: (# relevant docs retrieved in top-k) / (total # relevant docs)
        
        Example:
            Total relevant docs: 10
            Found in top 50: 7
            Recall@50 = 7/10 = 0.7
        """
        if len(relevant_docs) == 0:
            return 0.0
        
        relevant_count = 0
        for result in results[:k]:
            doc_id = result.get('url') or result.get('title')
            if doc_id in relevant_docs:
                relevant_count += 1
        
        return relevant_count / len(relevant_docs)
    
    
    @staticmethod
    def ndcg_at_k(results: List[Dict], relevant_docs: List[str], k: int = 10) -> float:
        """
        nDCG@k: Normalized Discounted Cumulative Gain
        Measures ranking quality - penalizes relevant docs that are ranked low
        
        Formula:
            DCG@k = Sum(relevance_i / log2(i+1)) for i=1 to k
            iDCG@k = DCG of ideal ranking
            nDCG@k = DCG@k / iDCG@k
        
        Example:
            Top 10: [relevant, relevant, irrelevant, relevant, ...]
            DCG higher if relevant docs are at top (small log2 values)
            nDCG@10 = 0.7 means 70% as good as perfect ranking
        """
        if len(relevant_docs) == 0:
            return 0.0
        
        # Calculate DCG
        dcg = 0.0
        for i, result in enumerate(results[:k]):
            doc_id = result.get('url') or result.get('title')
            relevance = 1 if doc_id in relevant_docs else 0
            dcg += relevance / math.log2(i + 2)  # i+2 because ranking starts at 1
        
        # Calculate ideal DCG (all relevant docs ranked first)
        idcg = 0.0
        for i in range(min(k, len(relevant_docs))):
            idcg += 1 / math.log2(i + 2)
        
        # Calculate nDCG
        if idcg == 0:
            return 0.0
        
        return dcg / idcg
    
    
    @staticmethod
    def mrr(results: List[Dict], relevant_docs: List[str]) -> float:
        """
        MRR: Mean Reciprocal Rank
        How far down the results is the first relevant doc?
        
        Formula: 1 / (rank of first relevant document)
        
        Example:
            Top 3: [irrelevant, relevant, irrelevant]
            First relevant at rank 2
            MRR = 1/2 = 0.5
        """
        for i, result in enumerate(results):
            doc_id = result.get('url') or result.get('title')
            if doc_id in relevant_docs:
                return 1.0 / (i + 1)  # +1 because ranking starts at 1
        
        return 0.0  # No relevant doc found


def load_labeled_queries(filepath: str) -> List[Dict]:
    """
    Load labeled test queries.
    
    Format (CSV):
        query,doc_url,relevant
        "Bangladesh politics","https://...",yes
        "Bangladesh politics","https://...",no
        ...
    """
    queries = {}
    
    try:
        import csv
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                query = row['query'].strip()
                url = row['doc_url'].strip()
                relevant = row['relevant'].strip().lower() == 'yes'
                
                if query not in queries:
                    queries[query] = {'relevant': [], 'irrelevant': []}
                
                if relevant:
                    queries[query]['relevant'].append(url)
                else:
                    queries[query]['irrelevant'].append(url)
        
        return queries
    except Exception as e:
        print(f"❌ Error loading queries: {e}")
        return {}


def calculate_metrics(results: List[Dict], relevant_docs: List[str]) -> Dict:
    """Calculate all metrics for a query."""
    
    metrics = AccuracyMetrics()
    
    return {
        'precision@10': metrics.precision_at_k(results, relevant_docs, k=10),
        'recall@50': metrics.recall_at_k(results, relevant_docs, k=50),
        'ndcg@10': metrics.ndcg_at_k(results, relevant_docs, k=10),
        'mrr': metrics.mrr(results, relevant_docs),
    }


def print_metrics(metrics: Dict, query: str):
    """Print metrics nicely."""
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    p10 = metrics.get('precision@10', 0)
    r50 = metrics.get('recall@50', 0)
    ndcg = metrics.get('ndcg@10', 0)
    mrr = metrics.get('mrr', 0)
    
    print(f"  Precision@10:  {p10:.3f}  (target >= 0.6)")
    print(f"  Recall@50:     {r50:.3f}  (target >= 0.5)")
    print(f"  nDCG@10:       {ndcg:.3f}  (target >= 0.5)")
    print(f"  MRR:           {mrr:.3f}  (target >= 0.4)")
    
    # Pass/fail
    passed = 0
    if p10 >= 0.6:
        print("  ✅ Precision@10 PASSED")
        passed += 1
    else:
        print("  ❌ Precision@10 FAILED")
    
    if r50 >= 0.5:
        print("  ✅ Recall@50 PASSED")
        passed += 1
    else:
        print("  ❌ Recall@50 FAILED")
    
    if ndcg >= 0.5:
        print("  ✅ nDCG@10 PASSED")
        passed += 1
    else:
        print("  ❌ nDCG@10 FAILED")
    
    if mrr >= 0.4:
        print("  ✅ MRR PASSED")
        passed += 1
    else:
        print("  ❌ MRR FAILED")
    
    print(f"\n  Result: {passed}/4 metrics passed")


def example_usage():
    """Show example of how to use metrics."""
    
    print("\n" + "="*60)
    print("EXAMPLE: How to Calculate Accuracy")
    print("="*60 + "\n")
    
    # Example search results
    example_results = [
        {'url': 'https://example.com/1', 'title': 'Relevant 1'},
        {'url': 'https://example.com/2', 'title': 'Not relevant'},
        {'url': 'https://example.com/3', 'title': 'Relevant 2'},
        {'url': 'https://example.com/4', 'title': 'Relevant 3'},
        {'url': 'https://example.com/5', 'title': 'Not relevant'},
        {'url': 'https://example.com/6', 'title': 'Not relevant'},
        {'url': 'https://example.com/7', 'title': 'Relevant 4'},
        {'url': 'https://example.com/8', 'title': 'Not relevant'},
        {'url': 'https://example.com/9', 'title': 'Relevant 5'},
        {'url': 'https://example.com/10', 'title': 'Relevant 6'},
    ]
    
    # Relevant docs you marked manually
    relevant_docs = [
        'https://example.com/1',
        'https://example.com/3',
        'https://example.com/4',
        'https://example.com/7',
        'https://example.com/9',
        'https://example.com/10',
        'https://example.com/11',  # In collection but not retrieved
        'https://example.com/12',  # In collection but not retrieved
    ]
    
    print("Top 10 results:")
    for i, r in enumerate(example_results, 1):
        is_relevant = r['url'] in relevant_docs
        status = "✅" if is_relevant else "❌"
        print(f"  {i}. {status} {r['url']}")
    
    # Calculate metrics
    metrics = calculate_metrics(example_results, relevant_docs)
    print_metrics(metrics, "Example Query")
    
    print("\nInterpretation:")
    print("  • 6 out of 10 top results are relevant (60% precision)")
    print("  • Found 6 out of 8 relevant docs (75% recall@50)")
    print("  • Ranking is good - relevant docs mostly at top (nDCG~0.7)")
    print("  • First relevant doc at rank 1 (MRR = 1.0)")


if __name__ == "__main__":
    example_usage()
    
    print("\n\n" + "="*60)
    print("TO USE WITH YOUR DATA:")
    print("="*60 + "\n")
    
    print("""
1. Create labels CSV file with structure:
   query,doc_url,relevant
   "Bangladesh politics","https://...",yes
   "Bangladesh politics","https://...",no
   
2. Load labeled queries:
   queries = load_labeled_queries('data/labeled_queries.csv')
   
3. For each query, run search and calculate metrics:
   results = semantic.search(query, k=50)
   metrics = calculate_metrics(results, queries[query]['relevant'])
   print_metrics(metrics, query)

4. Average metrics across all queries to get overall performance
    """)
