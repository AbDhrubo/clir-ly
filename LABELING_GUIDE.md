# Query Labeling Guide

## Quick Start: 3 Steps to Label Queries

### Step 1: Run Search on Your System

For each test query, run your hybrid search and get the top 50 results:

```python
# Create a labeling helper script
python scripts/generate_labeling_csv.py
```

This will:
1. Load your articles
2. Run search on predefined queries
3. Generate a CSV with all results ready for you to label

### Step 2: Label the Results

Open `data/labeled_queries.csv` and for each result, mark:
- `relevant` = "yes" if the document is relevant to the query
- `relevant` = "no" if the document is NOT relevant

**What makes a document relevant?**
- **On-topic**: Matches the query intent
- **Informative**: Contains useful information about the topic
- **Not just keyword match**: Actually about the topic, not just mentions it

### Step 3: Run Evaluation

```bash
python scripts/run_evaluation.py
```

---

## Detailed Instructions

### What You're Doing

You're creating "ground truth" - manually deciding which documents are truly relevant to each query. This allows you to measure how well your system performs.

### Example: Labeling "Bangladesh politics"

Run search:
```python
from src.retrieval.hybrid import HybridSearch
import json

# Load articles
articles = []
with open('data/processed/articles_all.jsonl', 'r') as f:
    for line in f:
        articles.append(json.loads(line))

# Initialize search
hybrid = HybridSearch(articles)

# Search
results = hybrid.search("Bangladesh politics", k=50)

# Now manually review each result
```

For each result, ask yourself:
- ✅ Is this about Bangladesh politics? → relevant = "yes"
- ❌ Is this about sports/entertainment/other? → relevant = "no"

### Sample Labeling Decisions

**Query: "Bangladesh politics"**

✅ **YES** - Relevant:
- "PM announces new cabinet reshuffle"
- "Election commission sets vote date"
- "Parliament passes new legislation"

❌ **NO** - Not Relevant:
- "Bangladesh cricket team wins match" (sports, not politics)
- "Dhaka traffic situation worsens" (local news, not politics)
- "New shopping mall opens in Chittagong" (business, not politics)

### Tips for Good Labeling

1. **Be Consistent**: Apply the same criteria across all queries
2. **Be Realistic**: Not everything mentioning a keyword is relevant
3. **Consider User Intent**: Would this answer the user's question?
4. **Binary Choice**: Either relevant or not - no maybe
5. **Don't Overthink**: Trust your instinct as a user

### How Many to Label?

**Minimum**: 
- 5 queries
- Top 20 results per query
- = 100 labels total

**Recommended**:
- 5-10 queries
- Top 50 results per query
- = 250-500 labels total

**More labels = more accurate evaluation!**

### Using the Helper Script

I'll create a helper script that makes this easier:

```bash
# Generate CSV with search results ready for labeling
python scripts/generate_labeling_csv.py

# This creates data/labeled_queries_DRAFT.csv with all results
# You just need to fill in the "relevant" column!
```

### Manual Process (Alternative)

If you prefer to do it manually:

1. Open your system in Python/notebook
2. For each query, run search and get top 50
3. Review each result's title and snippet
4. Add a row to CSV for each result
5. Mark relevant="yes" or "no"

### Time Estimate

- 5 queries × 50 results = 250 labels
- ~30 seconds per label (read, decide, mark)
- **Total: ~2 hours of focused work**

Break it into sessions:
- Session 1: Label 2 queries (~50 min)
- Session 2: Label 2 queries (~50 min)
- Session 3: Label 1 query (~25 min)

### Quality Check

Before running evaluation:
- [ ] All queries have at least 20 labeled results
- [ ] Mix of "yes" and "no" labels (not all yes or all no)
- [ ] At least 5 different queries
- [ ] Both English and Bangla queries included
- [ ] CSV is properly formatted

### What Happens Next

After labeling:
```bash
python scripts/run_evaluation.py
```

This will:
- Calculate Precision@10 (how many of top 10 are relevant?)
- Calculate Recall@50 (did you find the relevant docs?)
- Calculate nDCG@10 (are relevant docs ranked high?)
- Calculate MRR (where's the first relevant doc?)

Good luck! 🎯
