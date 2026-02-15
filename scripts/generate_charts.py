#!/usr/bin/env python3
"""
Generate evaluation charts for the CLIR-ly report.

Outputs (PDF for LaTeX inclusion):
  report/figures/radar_method_comparison.pdf
  report/figures/score_boxplots.pdf
  report/figures/bn_vs_en_performance.pdf
  report/figures/time_vs_quality.pdf
"""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────
BASE    = Path('/home/user/clir-ly')
RES_DIR = BASE / 'results'
FIG_DIR = BASE / 'report' / 'figures'
FIG_DIR.mkdir(parents=True, exist_ok=True)

METHODS = {
    'BM25':     ('bm25_results.json',            'combined_top10', 'score'),
    'Fuzzy':    ('fuzzy_results.json',            'combined_top10', 'score'),
    'Semantic': ('semantic_results_labse.json',   'combined_top10', 'score'),
    'Hybrid':   ('hybrid_results_labse.json',     'results',        'hybrid_score'),
}

COLORS = {
    'BM25':     '#2196F3',
    'Fuzzy':    '#FF9800',
    'Semantic': '#4CAF50',
    'Hybrid':   '#E91E63',
}

# ── Helpers ────────────────────────────────────────────────────────────
def load(fname):
    with open(RES_DIR / fname) as f:
        return json.load(f)

def top1_score(query_data, results_key, score_key):
    """Return the top-1 score for a query, normalized to 0-100."""
    docs = query_data[results_key]
    if not docs:
        return 0.0
    raw = docs[0][score_key]
    # BM25 raw scores are unbounded; others are already 0-100
    # For BM25, cap at 100 for consistent comparison
    if score_key == 'score' and raw > 100:
        return min(raw, 100.0)
    return raw


# ── Load all data ─────────────────────────────────────────────────────
all_data = {}
for method, (fname, rkey, skey) in METHODS.items():
    all_data[method] = load(fname)


# ======================================================================
# CHART 2: Radar / Spider Chart  (Method Comparison)
# ======================================================================
def make_radar():
    # Pre-computed metrics from the report (Table 5 / eval_metrics)
    metrics = {
        'P@10':      {'BM25': 0.66, 'Fuzzy': 0.31, 'Semantic': 0.53, 'Hybrid': 0.63},
        'Recall@50': {'BM25': 0.92, 'Fuzzy': 0.57, 'Semantic': 0.79, 'Hybrid': 0.86},
        'nDCG@10':   {'BM25': 0.85, 'Fuzzy': 0.55, 'Semantic': 0.78, 'Hybrid': 0.88},
        'MRR':       {'BM25': 0.90, 'Fuzzy': 0.49, 'Semantic': 0.82, 'Hybrid': 0.93},
        'Avg Speed\n(norm)': {},  # will fill from data — inverted so higher = faster
    }

    # Compute average speed per method, then normalize (invert: fastest = 1.0)
    avg_times = {}
    for method, queries in all_data.items():
        times = [q['execution_time_ms'] for q in queries]
        avg_times[method] = sum(times) / len(times)

    max_time = max(avg_times.values())
    for method, t in avg_times.items():
        metrics['Avg Speed\n(norm)'][method] = 1.0 - (t / max_time)  # faster → higher

    labels = list(metrics.keys())
    n = len(labels)
    angles = [i * 2 * math.pi / n for i in range(n)]
    angles += angles[:1]  # close polygon

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))

    for method in METHODS:
        values = [metrics[lab][method] for lab in labels]
        values += values[:1]
        ax.plot(angles, values, 'o-', linewidth=2, label=method, color=COLORS[method])
        ax.fill(angles, values, alpha=0.08, color=COLORS[method])

    ax.set_thetagrids([a * 180 / math.pi for a in angles[:-1]], labels, fontsize=10)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8, color='grey')
    ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.12), fontsize=9)
    ax.set_title('Retrieval Method Comparison', fontsize=13, fontweight='bold', pad=20)

    fig.tight_layout()
    fig.savefig(FIG_DIR / 'radar_method_comparison.pdf', bbox_inches='tight')
    fig.savefig(FIG_DIR / 'radar_method_comparison.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  ✓ radar_method_comparison.pdf')


# ======================================================================
# CHART 3: Score Distribution Boxplots
# ======================================================================
def make_boxplots():
    fig, ax = plt.subplots(figsize=(7, 4.5))

    box_data = []
    method_names = []

    for method, (fname, rkey, skey) in METHODS.items():
        queries = all_data[method]
        scores = [top1_score(q, rkey, skey) for q in queries]
        box_data.append(scores)
        method_names.append(method)

    bp = ax.boxplot(
        box_data,
        labels=method_names,
        patch_artist=True,
        widths=0.5,
        showmeans=True,
        meanprops=dict(marker='D', markerfacecolor='white', markeredgecolor='black', markersize=6),
    )

    for patch, method in zip(bp['boxes'], method_names):
        patch.set_facecolor(COLORS[method])
        patch.set_alpha(0.6)
    for median in bp['medians']:
        median.set(color='black', linewidth=2)

    ax.set_ylabel('Top-1 Score', fontsize=11)
    ax.set_title('Top-1 Score Distribution by Retrieval Method', fontsize=13, fontweight='bold')
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # Annotate medians
    for i, scores in enumerate(box_data):
        med = sorted(scores)[len(scores) // 2]
        mean = sum(scores) / len(scores)
        ax.annotate(f'μ={mean:.1f}', xy=(i + 1, mean), xytext=(i + 1.3, mean + 2),
                     fontsize=8, color='grey')

    fig.tight_layout()
    fig.savefig(FIG_DIR / 'score_boxplots.pdf', bbox_inches='tight')
    fig.savefig(FIG_DIR / 'score_boxplots.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  ✓ score_boxplots.pdf')


# ======================================================================
# CHART 4: Bangla vs English Performance (Grouped Bar)
# ======================================================================
def make_bn_vs_en():
    fig, ax = plt.subplots(figsize=(8, 4.5))

    method_names = list(METHODS.keys())
    bn_means = []
    en_means = []

    for method, (fname, rkey, skey) in METHODS.items():
        queries = all_data[method]
        bn_scores = [top1_score(q, rkey, skey) for q in queries if q['language'] == 'bn']
        en_scores = [top1_score(q, rkey, skey) for q in queries if q['language'] == 'en']
        bn_means.append(sum(bn_scores) / len(bn_scores) if bn_scores else 0)
        en_means.append(sum(en_scores) / len(en_scores) if en_scores else 0)

    x = np.arange(len(method_names))
    w = 0.32

    bars_bn = ax.bar(x - w/2, bn_means, w, label='Bangla (13 queries)', color='#1565C0', alpha=0.8)
    bars_en = ax.bar(x + w/2, en_means, w, label='English (10 queries)', color='#E53935', alpha=0.8)

    # Value labels on top of bars
    for bar in bars_bn:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                f'{bar.get_height():.1f}', ha='center', va='bottom', fontsize=8)
    for bar in bars_en:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                f'{bar.get_height():.1f}', ha='center', va='bottom', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(method_names, fontsize=11)
    ax.set_ylabel('Mean Top-1 Score', fontsize=11)
    ax.set_title('Bangla vs English Query Performance', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_ylim(0, max(bn_means + en_means) * 1.15)

    fig.tight_layout()
    fig.savefig(FIG_DIR / 'bn_vs_en_performance.pdf', bbox_inches='tight')
    fig.savefig(FIG_DIR / 'bn_vs_en_performance.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  ✓ bn_vs_en_performance.pdf')


# ======================================================================
# CHART 5: Execution Time vs Quality (Scatter)
# ======================================================================
def make_time_vs_quality():
    fig, ax = plt.subplots(figsize=(7, 5))

    # Pre-computed nDCG@10 from report
    ndcg = {'BM25': 0.85, 'Fuzzy': 0.55, 'Semantic': 0.78, 'Hybrid': 0.88}

    for method, queries in all_data.items():
        times = [q['execution_time_ms'] for q in queries]
        avg_time = sum(times) / len(times)
        quality = ndcg[method]

        ax.scatter(avg_time, quality, s=200, c=COLORS[method], edgecolors='black',
                   linewidths=1.2, zorder=5, label=method)
        # Label next to point
        offset_x = 300
        offset_y = 0.015
        ax.annotate(method, (avg_time, quality),
                    xytext=(avg_time + offset_x, quality + offset_y),
                    fontsize=10, fontweight='bold', color=COLORS[method])

    ax.set_xlabel('Average Query Time (ms)', fontsize=11)
    ax.set_ylabel('nDCG@10', fontsize=11)
    ax.set_title('Speed–Quality Tradeoff', fontsize=13, fontweight='bold')

    # Target line
    ax.axhline(y=0.50, color='grey', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(ax.get_xlim()[0] + 200, 0.51, 'Target ≥ 0.50', fontsize=8, color='grey')

    ax.yaxis.grid(True, alpha=0.3)
    ax.xaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.set_ylim(0.4, 1.0)

    # Format x-axis with comma separators
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

    fig.tight_layout()
    fig.savefig(FIG_DIR / 'time_vs_quality.pdf', bbox_inches='tight')
    fig.savefig(FIG_DIR / 'time_vs_quality.png', dpi=200, bbox_inches='tight')
    plt.close(fig)
    print('  ✓ time_vs_quality.pdf')


# ── Main ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('Generating charts...')
    make_radar()
    make_boxplots()
    make_bn_vs_en()
    make_time_vs_quality()
    print(f'\nAll figures saved to {FIG_DIR}/')
