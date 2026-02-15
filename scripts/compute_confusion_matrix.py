#!/usr/bin/env python3
"""
Compute confusion matrices and classification metrics for IR methods.
"""

import json
import csv
from collections import defaultdict
from pathlib import Path

def load_ground_truth(csv_path):
    """Load ground truth relevance from CSV."""
    ground_truth = defaultdict(set)  # query -> set of relevant URLs

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            query = row['query'].strip()
            url = row['url'].strip()
            relevant = row['relevant'].strip().lower() == 'yes'

            if relevant and url:  # Only add if URL is not empty
                ground_truth[query].add(url)

    return ground_truth

def load_results(json_path):
    """Load retrieval results from JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compute_confusion_matrix(results, ground_truth, k=10):
    """
    Compute confusion matrix for retrieval results.

    For each query:
    - TP: relevant docs in top-K
    - FP: non-relevant docs in top-K
    - FN: relevant docs not in top-K
    - TN: non-relevant docs not in top-K (approximated)
    """
    total_tp = 0
    total_fp = 0
    total_fn = 0
    total_tn = 0

    query_metrics = []

    for query_data in results:
        query = query_data['raw_query']
        relevant_urls = ground_truth.get(query, set())

        # Get top-K results
        if 'results' in query_data:  # Hybrid format
            top_k = query_data['results'][:k]
            retrieved_urls = {doc['url'] for doc in top_k}
        else:  # BM25, Fuzzy, Semantic format
            top_k = query_data.get('combined_top10', [])[:k]
            retrieved_urls = {doc['url'] for doc in top_k}

        # Compute TP, FP, FN
        tp = len(retrieved_urls & relevant_urls)
        fp = len(retrieved_urls - relevant_urls)
        fn = len(relevant_urls - retrieved_urls)

        # TN is approximated (all non-relevant docs not retrieved)
        # For simplicity, we'll estimate based on a fixed corpus size
        # Assuming ~5000 documents in corpus
        corpus_size = 5062
        tn = corpus_size - k - fn  # Approximate

        total_tp += tp
        total_fp += fp
        total_fn += fn
        total_tn += tn

        # Per-query metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        query_metrics.append({
            'query': query,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'precision': precision,
            'recall': recall,
            'f1': f1
        })

    # Overall metrics
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (total_tp + total_tn) / (total_tp + total_fp + total_fn + total_tn) if (total_tp + total_fp + total_fn + total_tn) > 0 else 0

    return {
        'confusion_matrix': {
            'TP': total_tp,
            'FP': total_fp,
            'FN': total_fn,
            'TN': total_tn
        },
        'metrics': {
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'accuracy': accuracy
        },
        'query_metrics': query_metrics
    }

def main():
    base_dir = Path.cwd()  # Uses current working directory
    results_dir = Path('results')

    # Load ground truth
    ground_truth = load_ground_truth(base_dir / 'data' / 'search_results.csv')

    print(f"Loaded ground truth for {len(ground_truth)} queries")
    print(f"Total relevant URLs: {sum(len(urls) for urls in ground_truth.values())}")
    print()

    methods = {
        'BM25': 'bm25_results.json',
        'Fuzzy': 'fuzzy_results.json',
        'Semantic (LaBSE)': 'semantic_results_labse.json',
        'Hybrid': 'hybrid_results_labse.json'
    }

    all_results = {}

    for method_name, filename in methods.items():
        print(f"=== {method_name} ===")

        results = load_results(results_dir / filename)
        analysis = compute_confusion_matrix(results, ground_truth, k=10)

        cm = analysis['confusion_matrix']
        metrics = analysis['metrics']

        print(f"Confusion Matrix:")
        print(f"  TP: {cm['TP']:4d}  FP: {cm['FP']:4d}")
        print(f"  FN: {cm['FN']:4d}  TN: {cm['TN']:4d}")
        print()
        print(f"Classification Metrics:")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall:    {metrics['recall']:.4f}")
        print(f"  F1-Score:  {metrics['f1_score']:.4f}")
        print(f"  Accuracy:  {metrics['accuracy']:.4f}")
        print()

        all_results[method_name] = analysis

    # Save results
    output_file = results_dir / 'confusion_matrix_analysis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {output_file}")

    # Generate LaTeX table
    print("\n=== LaTeX Confusion Matrix Table ===")
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Confusion Matrices and Classification Metrics (K=10)}")
    print(r"\begin{tabular}{lcccc|cccc}")
    print(r"\hline")
    print(r"\textbf{Method} & \textbf{TP} & \textbf{FP} & \textbf{FN} & \textbf{TN} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} & \textbf{Accuracy} \\")
    print(r"\hline")

    for method_name in methods.keys():
        cm = all_results[method_name]['confusion_matrix']
        metrics = all_results[method_name]['metrics']

        print(f"{method_name} & {cm['TP']} & {cm['FP']} & {cm['FN']} & {cm['TN']} & "
              f"{metrics['precision']:.3f} & {metrics['recall']:.3f} & "
              f"{metrics['f1_score']:.3f} & {metrics['accuracy']:.3f} \\\\")

    print(r"\hline")
    print(r"\end{tabular}")
    print(r"\label{tab:confusion-matrix}")
    print(r"\end{table}")

if __name__ == '__main__':
    main()
