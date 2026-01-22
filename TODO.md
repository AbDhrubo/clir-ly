# What's Done vs What's Left

## ✅ DONE

### Module A - Data Collection (COMPLETE)
- 5,062 articles crawled (2,525 English, 2,537 Bangla) 
- All metadata present: title, body, url, date, language, tokens, entities
- Data at: `notebooks/data/articles_with_ner.jsonl` & `data/processed/articles_all.jsonl`
- Knowledge graph built and visualized

### Module B - Query Processing (COMPLETE) ✅
- ✅ Language detection (`src/query/detector.py`)
- ✅ Query translation English ↔ Bangla (`src/query/translator.py`)
- ✅ Query processor pipeline (`src/query/processor.py`)
- ✅ Cross-lingual query expansion integrated

### Module C - Retrieval (COMPLETE) ✅
- ✅ BM25 search (`src/retrieval/bm25.py`)
- ✅ Fuzzy search (`src/retrieval/fuzzy.py`)
- ✅ Semantic search with LaBSE (`src/retrieval/semantic.py`)
- ✅ Hybrid search with weighted combination (`src/retrieval/hybrid.py`)
- ✅ Score normalization to [0-1] range
- ✅ Top-K ranking implemented
- ✅ Cross-lingual retrieval working
- ✅ Test scripts: `scripts/test_*.py`, `scripts/hybrid_search.py`

### Module D - Ranking & Scoring (PARTIAL) ⚠️
- ✅ Ranking function outputs sorted top-K documents
- ✅ Matching score normalization [0-1] implemented
- ✅ Query execution time tracking (total time in ms) - implemented in `scripts/hybrid_search.py`
- ✅ Evaluation metrics code: Precision@10, Recall@50, nDCG@10, MRR (`scripts/accuracy_metrics.py`)
- ❌ **Low-confidence warning NOT implemented** (threshold + warning message)
- ❌ **Query time breakdown NOT implemented** (translation time, embedding time, ranking time)
- ❌ **Comparison with classical search engines NOT done** (Google, Bing, DuckDuckGo)
- ❌ Test queries NOT labeled yet (need 5-10 queries minimum)
- ❌ Evaluation NOT run yet
- ❌ **Detailed error analysis NOT done** (5 categories with case studies)

---

## ❌ TODO (Priority Order)

### 1. Complete Module D - Low Confidence Warning - 1 hour
- [ ] Add confidence threshold check (e.g., top_score < 0.20)
- [ ] Display warning message when confidence is low: ⚠️ Warning: Retrieved results may not be relevant. Matching confidence is low (score: 0.15). Consider rephrasing your query or checking translation quality.
- [ ] Implement in: `src/retrieval/hybrid.py` or create wrapper function
- [ ] Test with low-quality queries

### 2. Query Execution Time Breakdown - 1.5 hours
- [ ] Add time tracking for:
  - Translation time (ms)
  - Embedding computation time (ms)
  - Ranking time (ms)
  - Total retrieval time (ms) - already implemented
- [ ] Implement in: `src/retrieval/hybrid.py` or wrapper
- [ ] Report breakdown for each query in output/CSV

### 3. Comparison with Classical Search Engines - 3 hours
- [ ] Select 5-10 test queries (same as evaluation queries)
- [ ] Manually search on:
  - Google Search
  - Bing Search
  - DuckDuckGo
  - Optional: AI-powered search (Perplexity, Bing Chat, etc.)
- [ ] Document top-10 results from each engine
- [ ] Compare with your system's results

**Total Remaining: ~17.5 documents per query
  - Format: query, doc_url, language, relevant (yes/no), annotator
- [ ] Run evaluation script on all 4 methods (BM25, Fuzzy, Semantic, Hybrid)
- [ ] Generate results: Precision@10, Recall@50, nDCG@10, MRR
- [ ] Target metrics:
  - Precision@10 ≥ 0.6 (at least 6 relevant in top 10)
  - Recall@50 ≥ 0.5
  - nDCG@10 ≥ 0.5
  - MRR ≥ 0.4
- [ ] Save results to: `results/evaluation_metrics.csv`

### 5. Detailed Error Analysis - 4 hours
**Must include at least ONE detailed case study per category:**

- [ ] **1. Translation Failures**
  - Example: "চেয়ার" (chair) mistranslated to "Chairman"
  - Include: query text, translation, wrong documents retrieved, analysis
  
- [ ] **2. Named Entity Mismatch**
  - Example: "ঢাকা" (Dhaka) vs "Dhaka" cross-lingual mismatch
  - Include: NER output, why match failed, relevant docs missed
  
- [ ] **3. Semantic vs. Lexical Wins**
  - Example: "শিক্ষা" (education) → BM25 fails, semantic retrieves "স্কুল" (school)
  - Include: comparison of BM25 vs semantic results, why semantic won
  
- [ ] **4. Cross-Script Ambiguity**
  - Example: "Bangladesh" vs "বাংলাদেশ" vs "Bangla Desh" (two words)
  - Include: different representations, which system handles
  
- [ ] **5. Code-Switching**
  - Example: Mixed Bangla-English query handling
  - Include: query with mixed languages, system behavior

**For each case:**
- [ ] Screenshot or text output
- [ ] Querysearch_engine_comparison.csv` - Need to create
- `results/evaluation_metrics.csv` - Need to create
- `results/error_analysis.json` - Need to create
- `results/error_analysis_report.md` - Need to create
- `results/query_execution_time_breakdown.csvs
- [ ] Analysis of why it failed/succeeded
- [ ] Suggestions for improvement

- [ ] Save detailed analysis to: `results/error_analysis.json`
- [ ] Create summary document: `results/error_analysis_report.md`

### 4. Report (Module E) - 3 hours
- [ ] Literature review (3-5 CLIR papers)
- [ ] Methodology summary (all modules A-D)
- [ ] Results tables (metrics comparison)
- [ ] Error analysis discussion
- [ ] AI usage log

**Total Remaining: ~10 hours**

---

## 📊 FILES SUMMARY

### Data Files
- `notebooks/data/articles_with_ner.jsonl` - 5,062 articles with NER
- `data/processed/articles_all.jsonl` - Same, alternative location
- `data/test_queries.csv` - 12 test queries (not labeled)
- `data/labeled_queries_template.csv` - Template for labeling

### Module B (Query Processing) - ✅ DONE
- `src/query/detector.py` - Language detection
- `src/query/translator.py` - EN ↔ BN translation
- `src/query/processor.py` - Main query pipeline

### Module C (Retrieval) - ✅ DONE
- `src/retrieval/bm25.py` - BM25 search
- `src/retrieval/fuzzy.py` - Fuzzy matching
- `src/retrieval/semantic.py` - Semantic search (LaBSE)
- `src/retrieval/hybrid.py` - Hybrid combination

### Module D (Evaluation) - ⚠️ PARTIAL
- `scripts/accuracy_metrics.py` - Metrics calculator (ready)
- **Missing**: Low-confidence warning
- **Missing**: Labeled queries
- **Missing**: Evaluation results

### Test Scripts
- `scripts/hybrid_search.py` - Main hybrid search demo
- `scripts/search_demo.py` - Interactive demo
- `scripts/compare_retrieval.py` - Method comparison
- `scripts/test_module_b.py` - Query processing tests
- `scripts/bm25_search.py` - BM25 standalone
- `scripts/semantic_search.py` - Semantic standalone

### Results (To Be Generated)
- `results/bm25_results.json` - Exists
- `results/evaluation_metrics.csv` - Need to create
- `results/error_analysis.json` - Need to create