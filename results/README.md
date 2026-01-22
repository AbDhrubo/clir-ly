# Results Directory

This directory contains evaluation results and comparison data.

## Files

### Existing Results
- `bm25_results.csv` - BM25 search results
- `bm25_results.json` - BM25 search results (JSON format)

### To Be Generated (Module D Evaluation)

#### 1. IR Metrics Evaluation
Run: `python scripts/run_evaluation.py`

Generated files:
- `evaluation_metrics.csv` - Per-query metrics for all 4 methods
- `evaluation_report.md` - Comprehensive evaluation report

#### 2. Search Engine Comparison
Follow: `docs/SEARCH_ENGINE_COMPARISON_GUIDE.md`

Create manually:
- `search_engine_comparison.csv` - Results from Google/Bing/DuckDuckGo
- `search_engine_comparison_report.md` - Comparison analysis

#### 3. Error Analysis
Document case studies:
- `error_analysis.json` - Structured error cases
- `error_analysis_report.md` - Detailed analysis report

## Expected CSV Formats

### evaluation_metrics.csv
```csv
method,query,language,search_time_ms,num_relevant,precision@10,recall@50,ndcg@10,mrr
BM25,"Bangladesh politics",en,15.2,8,0.700,0.625,0.682,1.000
Semantic,"Bangladesh politics",en,234.5,8,0.800,0.750,0.785,1.000
...
```

### search_engine_comparison.csv
```csv
query,engine,language,rank,url,title,snippet,relevant,notes
"Bangladesh politics","google","en",1,"https://...","Title","Snippet","yes","Good match"
"Bangladesh politics","bing","en",1,"https://...","Title","Snippet","yes","Similar to Google"
...
```

## Target Metrics

| Metric | Target | What It Means |
|--------|--------|---------------|
| Precision@10 | >= 0.6 | At least 6/10 relevant |
| Recall@50 | >= 0.5 | Find 50% of relevant docs |
| nDCG@10 | >= 0.5 | Good ranking quality |
| MRR | >= 0.4 | First relevant in top 3 |

## How to Generate Results

1. **Label test queries** in `data/labeled_queries.csv`
2. **Run evaluation**: `python scripts/run_evaluation.py`
3. **Manual comparison**: Follow search engine guide
4. **Error analysis**: Document case studies

See `MODULE_D_EVALUATION_GUIDE.md` for detailed instructions.
