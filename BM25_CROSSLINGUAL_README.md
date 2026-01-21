"""
📖 BM25 CROSS-LINGUAL TEST - COLAB INSTRUCTIONS
================================================

Run this on Google Colab with GPU enabled.

## Step 1: Install Dependencies
```
!pip install -q sentence-transformers scikit-learn fuzzywuzzy python-Levenshtein transformers torch
```

## Step 2: Mount Google Drive (Optional)
```
from google.colab import drive
drive.mount('/content/drive')
```

## Step 3: Clone or Upload Repository
```
!git clone https://github.com/your-repo/clir-ly.git
%cd clir-ly
```

## Step 4: Run Cross-Lingual BM25 Test
```
!python scripts/test_bm25_crosslingual.py
```

Expected output:
- ✅ Load 5,000+ documents (English + Bangla mixed)
- ✅ Load 30 test queries
- ✅ BM25 initialized
- 30 query results showing:
  - Query in both EN and BN  
  - Time taken
  - Number of results from BOTH languages
  - Top results with language labels

Example output line:
[  1/30] ✅ EN | Bangladesh politics          | 45.2ms | 10 docs
  - 🔍 1. [0.856] Politics in Bangladesh... (en)
  - 🌐 2. [0.794] বাংলাদেশের রাজনীতি... (bn)
  - 🌐 3. [0.723] গণতান্ত্রিক প্রক্রিয়া... (bn)

Legend:
- 🔍 = Found in original language search
- 🌐 = Found in translated language search (cross-lingual)

## What's happening:

1. **Module B (Query Processing)** translates each query:
   - English query → Translated to Bangla
   - Bangla query → Translated to English

2. **BM25 Search** finds matches in BOTH languages:
   - Search 1: Original query on original-language docs
   - Search 2: Translated query on other-language docs
   - Results are merged and deduplicated

3. **Output Shows**:
   - Which language each result came from
   - Score/relevance for each result
   - Whether it was from original or translated search

## Key Metrics to Track:

- **Success Rate**: Should be 100% (30/30)
- **Average Time**: ~100-500ms per query (depends on index size)
- **Result Coverage**: Mix of English + Bangla results for all queries
- **Language Mixing**: Every query should return docs in BOTH languages

## Files Generated:
- `results/bm25_crosslingual_test_results.json` - Full results with all metrics

## Next Steps After Running:

1. Check results in JSON output
2. Note average time per query
3. Run other strategies: `test_fuzzy_crosslingual.py`, `test_semantic_crosslingual.py`
4. Compare timings and result quality
5. Optimize hybrid weights based on speed/accuracy tradeoff

## Troubleshooting:

If BM25 returns 0 results:
- Check that documents have 'title' and 'body' fields
- Verify at least one query word is in the index
- Check language detection is working

If Module B translation fails:
- First query load might be slow (downloading models)
- Fallback: searches original query only
- Check internet connection on Colab

If memory issues:
- Reduce limit in load_documents() from None to 2000
- Run on GPU runtime (Menu → Runtime → Change runtime type)
"""

print(__doc__)
