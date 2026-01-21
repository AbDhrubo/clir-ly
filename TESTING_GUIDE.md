# Module C - Individual Strategy Test Suite

Test each retrieval strategy independently on 30 test queries (15 English, 15 Bangla).

## Quick Start on Colab

```bash
# Clone and setup
!git clone https://github.com/YOUR_REPO/clir-ly.git
!cd clir-ly && pip install -r requirements.txt -q

# Test BM25 first
!python scripts/test_bm25_only.py

# Then test others individually
!python scripts/test_fuzzy_only.py
!python scripts/test_semantic_only.py
!python scripts/test_hybrid_only.py
```

## Test Files

| Script | Strategy | Time | Purpose |
|--------|----------|------|---------|
| `test_bm25_only.py` | BM25 (keywords) | ~5 sec | Fast, exact matching |
| `test_fuzzy_only.py` | Fuzzy (typos) | ~30 sec | Handle misspellings |
| `test_semantic_only.py` | Semantic (embeddings) | ~2 min | Cross-lingual, meaning-based |
| `test_hybrid_only.py` | Hybrid (combined) | ~2 min | Best of all 3 |

## Test Dataset

**File:** `data/test_queries.csv`

30 queries total:
- 15 English queries
- 15 Bangla queries

Categories:
- Politics, Cricket, Education, Economy, Sports, etc.

## Output for Each Test

```
Total Queries:     30
Successful:        30 ✅
Failed:            0 ❌
Success Rate:      100%

Total Time:        XXX ms
Average Time/Query: XX ms

SAMPLE RESULTS (First 3)
📝 Query: Bangladesh politics (EN)
   Time: 1.2ms
   Top 5 Results:
      1. [0.923] Bangladesh Election Results... (en)
      2. [0.891] রাজনীতিতে পরিবর্তনের হাওয়া... (bn)
      3. [0.856] Political Crisis in Dhaka... (en)

STATISTICS BY LANGUAGE
English Queries: 15, Avg Time: XX ms
Bangla Queries: 15, Avg Time: XX ms
```

Results saved to:
- `results/bm25_test_results.json`
- `results/fuzzy_test_results.json`
- `results/semantic_test_results.json`
- `results/hybrid_test_results.json`

## Running BM25 First

```bash
!python scripts/test_bm25_only.py
```

This is fastest (~5 seconds) and will give you a baseline for:
- Speed (should be 1-2 ms per query)
- Quality (how relevant are results?)
- Coverage (how many queries returned results?)

Then move to others to compare!

## After Testing All 4

Copy the summary stats from each output:
- Average time per query
- Success rate
- Quality observations from sample results

Then I'll recommend optimal hybrid weights!
