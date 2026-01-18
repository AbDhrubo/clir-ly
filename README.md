# clir-ly - Cross-Lingual Information Retrieval

## Project Structure
```
clir-system/
│
├── config/
│   └── config.yaml                  # URLs, model names, thresholds, API keys
│
├── data/
│   ├── queries.csv                  # Test queries with labels
│   └── metadata_links.txt           # Links to HuggingFace datasets
│
├── src/
│   ├── crawl/
│   │   ├── __init__.py
│   │   └── scraper.py               # Crawl news sites, save to HF
│   │
│   ├── index/
│   │   ├── __init__.py
│   │   ├── preprocessor.py          # Tokenize, NER, clean text
│   │   └── indexer.py               # Build inverted index
│   │
│   ├── query/
│   │   ├── __init__.py
│   │   ├── detector.py              # Language detection
│   │   ├── translator.py            # Query translation
│   │   ├── expander.py              # Synonym expansion
│   │   └── ne_mapper.py             # Named entity mapping
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── lexical.py               # BM25, TF-IDF
│   │   ├── fuzzy.py                 # Fuzzy/transliteration matching
│   │   ├── semantic.py              # Embedding-based search
│   │   └── hybrid.py                # Combined scoring
│   │
│   ├── ranking/
│   │   ├── __init__.py
│   │   └── ranker.py                # Score normalization, top-k results
│   │
│   └── evaluation/
│       ├── __init__.py
│       ├── metrics.py               # Precision, Recall, nDCG, MRR
│       └── error_analysis.py        # Failure case logging
│
├── scripts/
│   ├── 01_crawl_data.py             # Run crawler
│   ├── 02_build_index.py            # Build index from HF data
│   ├── 03_run_search.py             # Interactive search demo
│   └── 04_evaluate.py               # Run evaluation metrics
│
├── notebooks/
│   ├── exploration.ipynb            # Data exploration
│   └── results_viz.ipynb            # Graphs, error analysis
│
├── results/
│   ├── metrics.csv                  # Evaluation results
│   ├── error_cases.json             # Detailed failure examples
│   └── execution_times.csv          # Query latency breakdown
│
├── docs/
│   ├── literature_review.md         # Paper summaries
│   ├── ai_usage_log.md              # AI prompts & outputs
│   └── methodology.md               # System design documentation
│
├── app/
│   └── streamlit_app.py             # Optional: Simple web UI
│
├── README.md
├── requirements.txt
└── .gitignore
```
