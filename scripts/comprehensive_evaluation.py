#!/usr/bin/env python3
"""
Comprehensive evaluation with confusion matrix, P@K curves, and statistical analysis.
"""

import json
from collections import defaultdict
from pathlib import Path

def judge_relevance(query, doc, strict=False):
    """
    Automated relevance judgment based on keyword matching.
    Returns: 2 (highly relevant), 1 (partially relevant), 0 (not relevant)
    """
    query_lower = query.lower()
    title_lower = doc['title'].lower()
    body_lower = doc['body'].lower() if doc['body'] else ""

    # Query-specific relevance keywords
    relevance_patterns = {
        'শিক্ষা ব্যবস্থা বাংলাদেশ': {
            2: ['education system', 'শিক্ষা', 'university', 'school', 'educational'],
            1: ['student', 'teacher', 'learning', 'academic']
        },
        'বাংলাদেশ অর্থনীতি': {
            2: ['economy', 'অর্থনীতি', 'economic', 'gdp', 'growth'],
            1: ['trade', 'business', 'market', 'financial']
        },
        'বাংলাদেশ ব্যাংক': {
            2: ['bangladesh bank', 'central bank', 'bb.org', 'monetary'],
            1: ['banking', 'financial', 'currency']
        },
        'ঢাকা যানজট': {
            2: ['traffic', 'যানজট', 'congestion', 'dhaka traffic'],
            1: ['transport', 'vehicle', 'road']
        },
        'চেয়ার': {
            2: ['chair', 'চেয়ার', 'furniture', 'seat'],
            1: ['office', 'table', 'desk']
        },
        'বাংলাদেশ কৃষি সমস্যা': {
            2: ['agriculture', 'কৃষি', 'farming', 'crop'],
            1: ['rural', 'farmer', 'land']
        },
        'বেকারত্ব বাংলাদেশ': {
            2: ['unemployment', 'বেকারত্ব', 'jobless', 'employment'],
            1: ['job', 'work', 'labor']
        },
        'বাংলাদেশ ২০২৬ নির্বাচনের আলোচনা': {
            2: ['election', 'নির্বাচন', '2026', 'voting', 'electoral'],
            1: ['political', 'parliament', 'government']
        },
        'কক্সবাজার শরণার্থী': {
            2: ['refugee', 'শরণার্থী', "cox's bazar", 'rohingya'],
            1: ['camp', 'humanitarian', 'myanmar']
        },
        'শিবির': {
            2: ['shibir', 'শিবির', 'islami chhatrashibir', 'student'],
            1: ['organization', 'political', 'islam']
        },
        'আগুন নর্সিংদি': {
            2: ['fire', 'আগুন', 'narsingdi', 'নর্সিংদি', 'blaze'],
            1: ['accident', 'disaster', 'damage']
        },
        'বাংলাদেশে মুদ্রাস্ফীতি': {
            2: ['inflation', 'মুদ্রাস্ফীতি', 'price', 'cost of living'],
            1: ['economy', 'economic', 'market']
        },
        'আরএমজি শিল্পে শ্রমাধিকারের ঝুঁকি উন্নয়ন': {
            2: ['rmg', 'garment', 'labor rights', 'worker', 'শ্রম'],
            1: ['factory', 'textile', 'safety']
        },
        'ভূমিকম্প': {
            2: ['earthquake', 'ভূমিকম্প', 'seismic', 'tremor'],
            1: ['disaster', 'geological', 'preparedness']
        },
        'bangladesh economy growth': {
            2: ['economy', 'economic growth', 'gdp', 'development'],
            1: ['trade', 'business', 'financial']
        },
        'dhaka traffic congestion': {
            2: ['traffic', 'congestion', 'dhaka traffic', 'jam'],
            1: ['transport', 'vehicle', 'road']
        },
        'climate change impact in bangladesh': {
            2: ['climate change', 'environmental', 'global warming', 'weather'],
            1: ['temperature', 'flood', 'disaster']
        },
        'unemployment in bangladesh': {
            2: ['unemployment', 'jobless', 'employment rate'],
            1: ['job', 'work', 'labor market']
        },
        'rohingya refugee crisis in bangladesh': {
            2: ['rohingya', 'refugee', 'myanmar', 'crisis'],
            1: ['camp', 'humanitarian', 'border']
        },
        'bangladesh interim government reforms': {
            2: ['interim government', 'reform', 'governance', 'political'],
            1: ['government', 'administration', 'policy']
        },
        'bangladesh earthquake preparedness': {
            2: ['earthquake', 'preparedness', 'disaster', 'seismic'],
            1: ['safety', 'building', 'infrastructure']
        },
        'bangladesh garment worker heat stress': {
            2: ['garment', 'heat stress', 'worker', 'rmg', 'temperature'],
            1: ['factory', 'safety', 'health']
        },
        'bangladesh t20 world cup security concerns': {
            2: ['t20', 'world cup', 'cricket', 'security'],
            1: ['sports', 'tournament', 'icc']
        },
        'bangladesh quantum computing research': {
            2: ['quantum computing', 'quantum', 'research'],
            1: ['technology', 'science', 'computing']
        }
    }

    patterns = relevance_patterns.get(query, {2: [], 1: []})

    # Check for highly relevant keywords
    for keyword in patterns.get(2, []):
        if keyword in title_lower or keyword in body_lower:
            return 2

    # Check for partially relevant keywords
    for keyword in patterns.get(1, []):
        if keyword in title_lower or keyword in body_lower:
            return 1

    return 0

def compute_metrics_at_k(results, k_values=[5, 10, 20, 50]):
    """Compute precision, recall, F1 at different K values."""
    metrics = {}

    for query_data in results:
        query = query_data['raw_query']

        if 'results' in query_data:  # Hybrid format
            docs = query_data['results']
        else:  # BM25, Fuzzy, Semantic format
            docs = query_data.get('combined_top10', [])

        # Judge relevance for all docs
        judged_docs = [(doc, judge_relevance(query, doc)) for doc in docs[:max(k_values)]]

        for k in k_values:
            relevant_retrieved = sum(1 for doc, rel in judged_docs[:k] if rel > 0)
            total_relevant = sum(1 for doc, rel in judged_docs if rel > 0)  # Upper bound

            precision = relevant_retrieved / k if k > 0 else 0
            recall = relevant_retrieved / total_relevant if total_relevant > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            if query not in metrics:
                metrics[query] = {}

            metrics[query][k] = {
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'relevant_retrieved': relevant_retrieved
            }

    return metrics

def compute_confusion_matrix_at_k(results, k=10):
    """Compute confusion matrix treating top-K as positive predictions."""
    tp = fp = fn = 0

    for query_data in results:
        query = query_data['raw_query']

        if 'results' in query_data:  # Hybrid format
            docs = query_data['results'][:k]
        else:
            docs = query_data.get('combined_top10', [])[:k]

        for doc in docs:
            relevance = judge_relevance(query, doc)
            if relevance > 0:
                tp += 1  # Relevant and retrieved
            else:
                fp += 1  # Not relevant but retrieved

        # Count FN: relevant docs not in top-K (approximated)
        # This is hard without full corpus judgments, so we estimate based on recall
        all_docs = query_data.get('combined_top10', []) if 'results' not in query_data else query_data['results'][:50]
        total_relevant = sum(1 for doc in all_docs if judge_relevance(query, doc) > 0)
        fn += max(0, total_relevant - tp)

    # TN is approximated
    corpus_size = 5062
    queries_count = len(results)
    tn = (corpus_size * queries_count) - tp - fp - fn

    # Compute metrics
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0

    return {
        'confusion_matrix': {'TP': tp, 'FP': fp, 'FN': fn, 'TN': tn},
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'accuracy': accuracy
    }

def main():
    base_dir = Path('/home/user/clir-ly')
    results_dir = base_dir / 'results'

    methods = {
        'BM25': 'bm25_results.json',
        'Fuzzy': 'fuzzy_results.json',
        'Semantic': 'semantic_results_labse.json',
        'Hybrid': 'hybrid_results_labse.json'
    }

    all_results = {}

    print("=" * 70)
    print("CONFUSION MATRIX ANALYSIS (K=10)")
    print("=" * 70)
    print()

    for method_name, filename in methods.items():
        with open(results_dir / filename) as f:
            results = json.load(f)

        # Compute confusion matrix
        cm_analysis = compute_confusion_matrix_at_k(results, k=10)

        print(f"=== {method_name} ===")
        cm = cm_analysis['confusion_matrix']
        print(f"Confusion Matrix:")
        print(f"  TP: {cm['TP']:4d}  FP: {cm['FP']:4d}")
        print(f"  FN: {cm['FN']:4d}  TN: {cm['TN']:6d}")
        print()
        print(f"Metrics:")
        print(f"  Precision: {cm_analysis['precision']:.4f}")
        print(f"  Recall:    {cm_analysis['recall']:.4f}")
        print(f"  F1-Score:  {cm_analysis['f1_score']:.4f}")
        print(f"  Accuracy:  {cm_analysis['accuracy']:.4f}")
        print()

        all_results[method_name] = {
            'confusion_matrix': cm_analysis,
            'precision_at_k': compute_metrics_at_k(results, k_values=[5, 10, 20])
        }

    # Save results
    output_file = results_dir / 'comprehensive_evaluation.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"Results saved to {output_file}")

    # Generate LaTeX table for confusion matrix
    print("\n" + "=" * 70)
    print("LATEX TABLE: Confusion Matrix")
    print("=" * 70)
    print()
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Confusion Matrix Analysis at K=10}")
    print(r"\small")
    print(r"\begin{tabular}{lccccccc}")
    print(r"\hline")
    print(r"\textbf{Method} & \textbf{TP} & \textbf{FP} & \textbf{FN} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} & \textbf{Accuracy} \\")
    print(r"\hline")

    for method_name in methods.keys():
        cm = all_results[method_name]['confusion_matrix']['confusion_matrix']
        metrics = all_results[method_name]['confusion_matrix']

        print(f"{method_name} & {cm['TP']} & {cm['FP']} & {cm['FN']} & "
              f"{metrics['precision']:.3f} & {metrics['recall']:.3f} & "
              f"{metrics['f1_score']:.3f} & {metrics['accuracy']:.3f} \\\\")

    print(r"\hline")
    print(r"\end{tabular}")
    print(r"\label{tab:confusion-matrix}")
    print(r"\end{table}")

    # Generate P@K comparison table
    print("\n" + "=" * 70)
    print("LATEX TABLE: Precision at K")
    print("=" * 70)
    print()
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Precision at Different K Values}")
    print(r"\begin{tabular}{lccc}")
    print(r"\hline")
    print(r"\textbf{Method} & \textbf{P@5} & \textbf{P@10} & \textbf{P@20} \\")
    print(r"\hline")

    for method_name in methods.keys():
        p_at_k = all_results[method_name]['precision_at_k']

        # Average precision across all queries
        p5_values = [q[5]['precision'] for q in p_at_k.values()]
        p10_values = [q[10]['precision'] for q in p_at_k.values()]
        p20_values = [q[20]['precision'] for q in p_at_k.values()]

        p5_avg = sum(p5_values) / len(p5_values) if p5_values else 0
        p10_avg = sum(p10_values) / len(p10_values) if p10_values else 0
        p20_avg = sum(p20_values) / len(p20_values) if p20_values else 0

        print(f"{method_name} & {p5_avg:.3f} & {p10_avg:.3f} & {p20_avg:.3f} \\\\")

    print(r"\hline")
    print(r"\end{tabular}")
    print(r"\label{tab:precision-at-k}")
    print(r"\end{table}")

if __name__ == '__main__':
    main()
