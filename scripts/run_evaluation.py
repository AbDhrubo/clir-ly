#!/usr/bin/env python3
"""
Evaluation Runner - Module D
============================
Runs evaluation on labeled queries and calculates IR metrics.

Usage:
    python scripts/run_evaluation.py

Requirements:
    - Labeled queries CSV: data/labeled_queries.csv
    - At least 5-10 test queries
    - Each query should have multiple labeled documents (relevant/irrelevant)

Output:
    - Console: Per-query metrics
    - File: results/evaluation_metrics.csv
    - File: results/evaluation_report.md
"""

import sys
import json
import csv
from pathlib import Path
from typing import Dict, List
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.bm25 import BM25Search
from src.retrieval.fuzzy import FuzzySearch
from src.retrieval.semantic import SemanticSearch
from src.retrieval.hybrid import HybridSearch
from scripts.accuracy_metrics import AccuracyMetrics, calculate_metrics, print_metrics


def load_articles(limit=None):
    """Load articles from processed data."""
    print("\n" + "="*80)
    print("Loading Articles")
    print("="*80)
    
    articles = []
    with open('data/processed/articles_all.jsonl', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            articles.append(json.loads(line))
    
    print(f"✅ Loaded {len(articles)} articles")
    return articles


def load_labeled_queries(filepath='data/labeled_queries.csv'):
    """
    Load labeled queries from CSV.
    
    CSV format:
        query,doc_url,language,relevant,annotator
        "Bangladesh politics","https://...",en,yes,person1
        "Bangladesh politics","https://...",en,no,person1
    
    Returns:
        Dict: {query: {'relevant': [urls], 'irrelevant': [urls], 'language': str}}
    """
    print("\n" + "="*80)
    print("Loading Labeled Queries")
    print("="*80)
    
    queries = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                query = row['query'].strip()
                url = row['doc_url'].strip()
                relevant = row['relevant'].strip().lower() == 'yes'
                language = row.get('language', 'unknown').strip()
                
                if query not in queries:
                    queries[query] = {
                        'relevant': [],
                        'irrelevant': [],
                        'language': language
                    }
                
                if relevant:
                    queries[query]['relevant'].append(url)
                else:
                    queries[query]['irrelevant'].append(url)
        
        print(f"✅ Loaded {len(queries)} unique queries")
        for query, data in queries.items():
            rel_count = len(data['relevant'])
            irrel_count = len(data['irrelevant'])
            print(f"  • '{query}' ({data['language']}): {rel_count} relevant, {irrel_count} irrelevant")
        
        return queries
    
    except FileNotFoundError:
        print(f"❌ Error: File not found: {filepath}")
        print("\n💡 Tip: Create labeled queries first!")
        print("   1. Copy data/labeled_queries_template.csv to data/labeled_queries.csv")
        print("   2. Add your 5-10 test queries with labeled documents")
        print("   3. Run this script again")
        return {}
    
    except Exception as e:
        print(f"❌ Error loading queries: {e}")
        return {}


def run_search(search_engine, query, k=50):
    """
    Run search and convert results to standard format.
    
    Returns:
        List[Dict]: [{'url': str, 'title': str, 'score': float}, ...]
    """
    results = search_engine.search(query, k=k)
    
    # Convert to standard format
    standard_results = []
    for doc_id, score, doc, *extras in results:
        standard_results.append({
            'url': doc.get('url', ''),
            'title': doc.get('title', ''),
            'score': score
        })
    
    return standard_results


def evaluate_method(method_name, search_engine, queries, k_values={'k10': 10, 'k50': 50}):
    """
    Evaluate a search method on all queries.
    
    Args:
        method_name: Name of the method (e.g., 'BM25', 'Semantic', 'Hybrid')
        search_engine: Initialized search engine instance
        queries: Dict of labeled queries
        k_values: Dict of k values for metrics
    
    Returns:
        Dict: Aggregated metrics across all queries
    """
    print("\n" + "="*80)
    print(f"Evaluating: {method_name}")
    print("="*80)
    
    all_metrics = []
    query_results = []
    
    for query_text, query_data in queries.items():
        relevant_urls = query_data['relevant']
        language = query_data['language']
        
        print(f"\nQuery: '{query_text}' ({language})")
        print(f"  Relevant docs: {len(relevant_urls)}")
        
        # Run search
        start_time = time.time()
        results = run_search(search_engine, query_text, k=k_values['k50'])
        search_time = (time.time() - start_time) * 1000  # ms
        
        print(f"  Search time: {search_time:.2f} ms")
        print(f"  Retrieved: {len(results)} documents")
        
        # Calculate metrics
        metrics = calculate_metrics(results, relevant_urls)
        all_metrics.append(metrics)
        
        # Store for CSV output
        query_results.append({
            'method': method_name,
            'query': query_text,
            'language': language,
            'search_time_ms': search_time,
            'num_relevant': len(relevant_urls),
            **metrics
        })
        
        # Print metrics
        print(f"  Precision@10: {metrics['precision@10']:.3f}")
        print(f"  Recall@50:    {metrics['recall@50']:.3f}")
        print(f"  nDCG@10:      {metrics['ndcg@10']:.3f}")
        print(f"  MRR:          {metrics['mrr']:.3f}")
    
    # Calculate average metrics
    avg_metrics = {
        'precision@10': sum(m['precision@10'] for m in all_metrics) / len(all_metrics),
        'recall@50': sum(m['recall@50'] for m in all_metrics) / len(all_metrics),
        'ndcg@10': sum(m['ndcg@10'] for m in all_metrics) / len(all_metrics),
        'mrr': sum(m['mrr'] for m in all_metrics) / len(all_metrics),
    }
    
    print("\n" + "-"*80)
    print(f"{method_name} - Average Metrics Across All Queries:")
    print("-"*80)
    print(f"  Precision@10: {avg_metrics['precision@10']:.3f} (target >= 0.6)")
    print(f"  Recall@50:    {avg_metrics['recall@50']:.3f} (target >= 0.5)")
    print(f"  nDCG@10:      {avg_metrics['ndcg@10']:.3f} (target >= 0.5)")
    print(f"  MRR:          {avg_metrics['mrr']:.3f} (target >= 0.4)")
    
    # Check if targets met
    targets_met = 0
    if avg_metrics['precision@10'] >= 0.6:
        print("  ✅ Precision@10 PASSED")
        targets_met += 1
    else:
        print("  ❌ Precision@10 FAILED")
    
    if avg_metrics['recall@50'] >= 0.5:
        print("  ✅ Recall@50 PASSED")
        targets_met += 1
    else:
        print("  ❌ Recall@50 FAILED")
    
    if avg_metrics['ndcg@10'] >= 0.5:
        print("  ✅ nDCG@10 PASSED")
        targets_met += 1
    else:
        print("  ❌ nDCG@10 FAILED")
    
    if avg_metrics['mrr'] >= 0.4:
        print("  ✅ MRR PASSED")
        targets_met += 1
    else:
        print("  ❌ MRR FAILED")
    
    print(f"\n  Overall: {targets_met}/4 metrics passed")
    
    return {
        'method': method_name,
        'avg_metrics': avg_metrics,
        'query_results': query_results,
        'targets_met': targets_met
    }


def save_results(all_results, output_dir='results'):
    """Save evaluation results to CSV and markdown."""
    Path(output_dir).mkdir(exist_ok=True)
    
    # Save CSV
    csv_path = Path(output_dir) / 'evaluation_metrics.csv'
    print(f"\n💾 Saving results to {csv_path}")
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'method', 'query', 'language', 'search_time_ms', 'num_relevant',
            'precision@10', 'recall@50', 'ndcg@10', 'mrr'
        ])
        writer.writeheader()
        
        for result in all_results:
            for query_result in result['query_results']:
                writer.writerow(query_result)
    
    # Save markdown report
    md_path = Path(output_dir) / 'evaluation_report.md'
    print(f"💾 Saving report to {md_path}")
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("# Evaluation Report - IR Metrics\n\n")
        f.write("## Overview\n\n")
        f.write(f"- **Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Queries Evaluated**: {len(all_results[0]['query_results']) if all_results else 0}\n")
        f.write(f"- **Methods Compared**: {len(all_results)}\n\n")
        
        f.write("## Target Metrics\n\n")
        f.write("| Metric | Target | Description |\n")
        f.write("|--------|--------|-------------|\n")
        f.write("| Precision@10 | >= 0.6 | At least 6 relevant docs in top 10 |\n")
        f.write("| Recall@50 | >= 0.5 | Find at least 50% of relevant docs |\n")
        f.write("| nDCG@10 | >= 0.5 | Good ranking quality |\n")
        f.write("| MRR | >= 0.4 | First relevant doc in top 3 on average |\n\n")
        
        f.write("## Results Summary\n\n")
        f.write("| Method | P@10 | R@50 | nDCG@10 | MRR | Targets Met |\n")
        f.write("|--------|------|------|---------|-----|-------------|\n")
        
        for result in all_results:
            m = result['avg_metrics']
            method = result['method']
            targets = result['targets_met']
            f.write(f"| {method} | {m['precision@10']:.3f} | {m['recall@50']:.3f} | "
                   f"{m['ndcg@10']:.3f} | {m['mrr']:.3f} | {targets}/4 |\n")
        
        f.write("\n## Detailed Results\n\n")
        
        for result in all_results:
            method = result['method']
            f.write(f"### {method}\n\n")
            f.write("| Query | Language | P@10 | R@50 | nDCG@10 | MRR | Time (ms) |\n")
            f.write("|-------|----------|------|------|---------|-----|----------|\n")
            
            for qr in result['query_results']:
                f.write(f"| {qr['query']} | {qr['language']} | {qr['precision@10']:.3f} | "
                       f"{qr['recall@50']:.3f} | {qr['ndcg@10']:.3f} | {qr['mrr']:.3f} | "
                       f"{qr['search_time_ms']:.1f} |\n")
            
            f.write("\n")
    
    print("✅ Results saved successfully!")


def main():
    """Main evaluation pipeline."""
    print("\n" + "="*80)
    print("MODULE D - EVALUATION RUNNER")
    print("="*80)
    
    # Load data
    articles = load_articles()
    queries = load_labeled_queries()
    
    if not queries:
        print("\n❌ No labeled queries found. Exiting.")
        print("\n📝 Next steps:")
        print("   1. Create data/labeled_queries.csv with your test queries")
        print("   2. Label at least 5-10 queries as relevant/irrelevant")
        print("   3. Run this script again")
        return
    
    print(f"\n✅ Ready to evaluate on {len(queries)} queries")
    
    # Initialize search methods
    print("\n" + "="*80)
    print("Initializing Search Methods")
    print("="*80)
    
    print("\n1️⃣  Initializing BM25...")
    bm25 = BM25Search(articles)
    
    print("\n2️⃣  Initializing Fuzzy Search...")
    fuzzy = FuzzySearch(articles, threshold=70)
    
    print("\n3️⃣  Initializing Semantic Search...")
    semantic = SemanticSearch(articles)
    
    print("\n4️⃣  Initializing Hybrid Search...")
    hybrid = HybridSearch(articles)
    
    # Run evaluation for each method
    all_results = []
    
    results_bm25 = evaluate_method('BM25', bm25, queries)
    all_results.append(results_bm25)
    
    results_fuzzy = evaluate_method('Fuzzy', fuzzy, queries)
    all_results.append(results_fuzzy)
    
    results_semantic = evaluate_method('Semantic', semantic, queries)
    all_results.append(results_semantic)
    
    results_hybrid = evaluate_method('Hybrid', hybrid, queries)
    all_results.append(results_hybrid)
    
    # Save results
    save_results(all_results)
    
    # Final summary
    print("\n" + "="*80)
    print("EVALUATION COMPLETE!")
    print("="*80)
    print("\n📊 Summary:")
    print("\n| Method | Targets Met |")
    print("|--------|-------------|")
    for result in all_results:
        print(f"| {result['method']} | {result['targets_met']}/4 |")
    
    print("\n📁 Output files:")
    print("  • results/evaluation_metrics.csv")
    print("  • results/evaluation_report.md")
    
    print("\n🎯 Next Steps:")
    print("  1. Review the evaluation report")
    print("  2. Compare with search engine baseline")
    print("  3. Perform error analysis on failed queries")
    print("  4. Document findings in your report")


if __name__ == "__main__":
    main()
