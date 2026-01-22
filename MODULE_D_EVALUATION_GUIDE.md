# Module D Evaluation - Quick Reference

## What You Need to Do Next

Your timing breakdown is **already implemented** ✅. Now you need to complete the evaluation:

### Step 1: Label Test Queries (Required)
**Time: ~2-3 hours**

1. Create `data/labeled_queries.csv` based on the template
2. Select 5-10 diverse queries:
   - Mix of English and Bangla
   - Different topics (politics, sports, education, etc.)
   - Include some challenging queries

3. For each query:
   - Run your search system
   - Review top 50 results
   - Label each as relevant (yes) or irrelevant (no)
   - Save to CSV

**CSV Format:**
```csv
query,doc_url,language,relevant,annotator
"Bangladesh politics","https://...",en,yes,yourname
"Bangladesh politics","https://...",en,no,yourname
"ঢাকায় শিক্ষা","https://...",bn,yes,yourname
```

### Step 2: Run Evaluation (Automated)
**Time: ~10 minutes**

```bash
# Once you have labeled queries
python scripts/run_evaluation.py
```

This will:
- Load your labeled queries
- Run BM25, Fuzzy, Semantic, and Hybrid search
- Calculate Precision@10, Recall@50, nDCG@10, MRR
- Generate results in `results/evaluation_metrics.csv`
- Create report in `results/evaluation_report.md`

**Target Metrics:**
- Precision@10 >= 0.6 (6/10 relevant)
- Recall@50 >= 0.5 (find 50%)
- nDCG@10 >= 0.5 (good ranking)
- MRR >= 0.4 (first relevant in top 3)

### Step 3: Compare with Search Engines
**Time: ~2-3 hours**

Follow the guide: `docs/SEARCH_ENGINE_COMPARISON_GUIDE.md`

1. Use same 5-10 queries from Step 1
2. Search on Google, Bing, DuckDuckGo
3. Document top 10 results from each
4. Save to `results/search_engine_comparison.csv`
5. Create comparison report

**Key Questions:**
- Can Google find Bangla content for English queries? (Usually no)
- Can your system do cross-lingual search? (Yes!)
- Where does your system excel? (Bangla queries, cross-lingual)
- Where do classical engines excel? (Web-scale, authority ranking)

### Step 4: Error Analysis
**Time: ~3-4 hours**

Analyze at least ONE case study per category:

1. **Translation Failures**: Query mistranslation hurting results
2. **Named Entity Mismatch**: "Dhaka" vs "ঢাকা" issues
3. **Semantic vs Lexical**: When semantic beats BM25
4. **Cross-Script Ambiguity**: Different representations
5. **Code-Switching**: Mixed language queries

For each:
- Show example query
- Show what went wrong
- Explain why
- Suggest improvements

## Quick Commands

```bash
# Test timing breakdown (already works!)
python test_timing_breakdown.py

# Run full evaluation (need labeled queries first)
python scripts/run_evaluation.py

# Test individual methods
python scripts/bm25_search.py
python scripts/semantic_search.py
python scripts/hybrid_search.py
```

## Files You Created Today

✅ `docs/SEARCH_ENGINE_COMPARISON_GUIDE.md` - Detailed comparison guide
✅ `scripts/run_evaluation.py` - Automated evaluation runner
✅ `notebooks/Module_D_LowConfidence_Colab.ipynb` - Updated with evaluation
✅ `TODO.md` - Updated progress tracking

## What's Already Working

✅ Query timing breakdown - fully implemented!
✅ Low confidence warnings - implemented!
✅ All 4 search methods - working!
✅ Evaluation metrics code - ready!

## What You Still Need

❌ Labeled test queries (5-10 queries)
❌ Run evaluation script
❌ Search engine comparison results
❌ Error analysis case studies

## Estimated Time Remaining

- Labeling queries: 2-3 hours
- Running evaluation: 10 minutes
- Search engine comparison: 2-3 hours  
- Error analysis: 3-4 hours
- **Total: ~8-11 hours**

## Tips

1. **Start with labeling** - That's the bottleneck
2. **Use diverse queries** - Mix English/Bangla, topics
3. **Be systematic** - Use same queries for all comparisons
4. **Document everything** - Screenshots, notes
5. **Focus on YOUR strengths** - Cross-lingual capability

Good luck! 🎯
