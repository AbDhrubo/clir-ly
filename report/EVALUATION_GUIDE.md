# Evaluation Guide — How to Complete the Evaluation

This document explains **exactly** how to run the evaluation for your CLIR system and fill in the remaining `---` placeholders in the LaTeX report.

---

## Overview: What Evaluation Means Here

You need to answer: **"When my system returns 10 results for a query, how many are actually relevant?"**

To answer this, you need:
1. **A set of test queries** (you already have 24 in `data/test_queries.csv` and `results/bm25_results.csv`)
2. **Relevance labels** (YOU manually judge whether each returned result is relevant)
3. **Metric computation** (the code in `scripts/run_evaluation.py` does this automatically)

---

## Step-by-Step Process

### Step 1: Pick 15-20 Test Queries (5 minutes)

You already have good queries from your results CSVs. Use a mix:

| # | Query | Language | Topic |
|---|-------|----------|-------|
| 1 | Bangladesh politics | en | Politics |
| 2 | Bangladesh economy growth | en | Economy |
| 3 | Dhaka traffic congestion | en | Urban |
| 4 | Rohingya refugee crisis in Bangladesh | en | Humanitarian |
| 5 | climate change impact in Bangladesh | en | Environment |
| 6 | Bangladesh T20 World Cup security concerns | en | Sports |
| 7 | unemployment in Bangladesh | en | Economy |
| 8 | Bangladesh interim government reforms | en | Politics |
| 9 | Bangladesh earthquake preparedness | en | Disaster |
| 10 | Bangladesh garment worker heat stress | en | Labor |
| 11 | বাংলাদেশ অর্থনীতি | bn | Economy |
| 12 | বাংলাদেশ ব্যাংক | bn | Finance |
| 13 | ঢাকা যানজট | bn | Urban |
| 14 | শিক্ষা ব্যবস্থা বাংলাদেশ | bn | Education |
| 15 | বাংলাদেশে মুদ্রাস্ফীতি | bn | Economy |
| 16 | কক্সবাজার শরণার্থী শিবির আগুন | bn | Humanitarian |
| 17 | বাংলাদেশ কৃষি সমস্যা | bn | Agriculture |
| 18 | চেয়ার | bn | Ambiguous |
| 19 | বেকারত্ব বাংলাদেশ | bn | Economy |
| 20 | আরএমজি শিল্পে শ্রমাধিকারের ঝুঁকি | bn | Labor |

### Step 2: Run Each Query Through Your System (30-60 minutes)

For each query, run the hybrid search and look at the top 10 results:

```python
# In a Python script or notebook:
from src.retrieval.hybrid import HybridSearch
import json

# Load articles
articles = []
with open('data/processed/articles_all.jsonl', 'r') as f:
    for line in f:
        articles.append(json.loads(line))

# Initialize
hybrid = HybridSearch(articles)

# Search
query = "Bangladesh politics"
results = hybrid.search(query, k=10)

# Print top 10
for rank, (doc_id, score, doc, *extras) in enumerate(results, 1):
    print(f"{rank}. [{score:.3f}] {doc['title'][:80]}")
    print(f"   URL: {doc.get('url', 'N/A')}")
    print()
```

### Step 3: Label Each Result as Relevant or Not (1-2 hours)

This is the **manual** part. For each query's top-10 results, ask yourself:

> "If I searched for this query, would this result answer my question?"

**Labeling criteria:**
- **YES (relevant):** The article is about the query topic, even if not a perfect match
- **NO (not relevant):** The article is about a completely different topic

**Create `data/labeled_queries.csv`** with this format:

```csv
query,doc_url,language,relevant,annotator
"Bangladesh politics","https://thedailystar.net/politics/article123",en,yes,YourName
"Bangladesh politics","https://prothomalo.com/sports/article456",bn,no,YourName
"Bangladesh politics","https://kalerkantho.com/rajniti/article789",bn,yes,YourName
```

**Tips:**
- Label ALL top-10 results for each query (so ~10 rows per query)
- Split the work: each group member labels 4-5 queries
- Use the article title to judge relevance (you don't need to read full articles)
- Be honest — some results WILL be irrelevant, and that's OK

### Step 4: Run the Evaluation Script (2 minutes)

```bash
python scripts/run_evaluation.py
```

This will:
1. Load your labeled queries from `data/labeled_queries.csv`
2. Run BM25, Fuzzy, Semantic, and Hybrid on each query
3. Compute Precision@10, Recall@50, nDCG@10, MRR
4. Save results to `results/evaluation_metrics.csv` and `results/evaluation_report.md`

### Step 5: Fill in the Report (10 minutes)

Take the numbers from `results/evaluation_report.md` and fill in Table 8 in the LaTeX report (the one with `---` placeholders).

---

## Understanding the Metrics

### Precision@10
**"Of the top 10 results, how many are relevant?"**

```
Precision@10 = (# relevant in top 10) / 10
```

Example: If 7 of your top 10 are relevant → P@10 = 0.70

**Target: ≥ 0.60**

### Recall@50
**"Of ALL relevant documents in the corpus, how many did we find in the top 50?"**

```
Recall@50 = (# relevant found in top 50) / (total # relevant docs)
```

Example: If there are 20 relevant docs total and you found 12 → R@50 = 0.60

**Target: ≥ 0.50**

Note: This metric depends on how many documents you labeled as relevant. If you only labeled 10 results per query, your "total relevant" is based on those labels.

### nDCG@10
**"Are the relevant results ranked at the TOP or buried at the bottom?"**

```
DCG@10 = Σ (relevance_i / log2(i+1))   for i = 1 to 10
nDCG@10 = DCG@10 / ideal_DCG@10
```

A relevant result at rank 1 contributes more than one at rank 10. If your relevant results are consistently at the top → nDCG close to 1.0.

**Target: ≥ 0.50**

### MRR (Mean Reciprocal Rank)
**"How far down is the FIRST relevant result?"**

```
MRR = 1 / (rank of first relevant doc)
```

- First relevant at rank 1 → MRR = 1.0
- First relevant at rank 2 → MRR = 0.5
- First relevant at rank 3 → MRR = 0.33

**Target: ≥ 0.40** (meaning first relevant result is typically in top 3)

---

## What Results to Expect

Based on the existing results in your CSVs, here's what you can reasonably expect:

| Method | Expected P@10 | Expected MRR | Why |
|--------|---------------|--------------|-----|
| BM25 | 0.40-0.60 | 0.50-0.80 | Good for exact keyword queries; fails on cross-lingual |
| Fuzzy | 0.20-0.40 | 0.30-0.50 | Often returns loosely related results |
| Semantic (LaBSE) | 0.50-0.70 | 0.60-0.90 | Best cross-lingual capability |
| Hybrid | 0.55-0.75 | 0.70-1.00 | Combines strengths of all methods |

**Honest results are better than inflated results.** The assignment rewards good error analysis — if BM25 scores 0.30, explain WHY (cross-script failure, synonym miss, etc.).

---

## Generating Plots for the Report

After evaluation, generate comparison plots:

```python
import matplotlib.pyplot as plt
import numpy as np

methods = ['BM25', 'Fuzzy', 'Semantic', 'Hybrid']
# TODO: Replace with your actual numbers from evaluation_metrics.csv
p10 = [0.45, 0.30, 0.60, 0.70]
r50 = [0.40, 0.25, 0.55, 0.65]
ndcg = [0.50, 0.35, 0.60, 0.72]
mrr = [0.60, 0.40, 0.75, 0.85]

x = np.arange(len(methods))
width = 0.2

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - 1.5*width, p10, width, label='P@10', color='#2196F3')
ax.bar(x - 0.5*width, r50, width, label='R@50', color='#4CAF50')
ax.bar(x + 0.5*width, ndcg, width, label='nDCG@10', color='#FF9800')
ax.bar(x + 1.5*width, mrr, width, label='MRR', color='#9C27B0')

ax.set_ylabel('Score')
ax.set_title('IR Metrics Comparison Across Retrieval Methods')
ax.set_xticks(x)
ax.set_xticklabels(methods)
ax.legend()
ax.set_ylim(0, 1.0)
ax.axhline(y=0.5, color='red', linestyle='--', alpha=0.5, label='Target baseline')
plt.tight_layout()
plt.savefig('report/figures/metrics_comparison.png', dpi=150)
plt.show()
```

Save plots as PNG files in `report/figures/` and include them in LaTeX with:
```latex
\includegraphics[width=0.8\textwidth]{figures/metrics_comparison.png}
```

---

## Quick Checklist

- [ ] Pick 15-20 test queries (mix of EN and BN)
- [ ] Run each query through all 4 methods
- [ ] Manually label top-10 results for each query as relevant/not-relevant
- [ ] Save labels in `data/labeled_queries.csv`
- [ ] Run `python scripts/run_evaluation.py`
- [ ] Copy numbers into LaTeX Table 8
- [ ] Generate comparison bar chart
- [ ] Generate timing breakdown chart
- [ ] Write 2-3 sentences interpreting the results

---

## Common Pitfalls to Avoid

1. **Don't inflate labels.** If a result is not relevant, mark it as "no". Honest results with good analysis score better than fake perfect results.

2. **Don't label too few queries.** The assignment requires at least 15 labeled queries. More is better (20-25 is ideal).

3. **Don't forget cross-lingual queries.** Include queries where an English query should find Bangla docs and vice versa. This is the whole point of CLIR.

4. **Don't skip the timing breakdown.** The assignment explicitly asks for retrieval time analysis. Your results CSVs already have `Time(ms)` columns — use them.

5. **Don't only show successes.** The error analysis section is worth 10% of the grade. Show failures honestly and explain why they happen.
