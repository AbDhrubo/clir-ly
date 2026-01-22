#!/usr/bin/env python3
"""
Quick Verification Script for Low-Confidence Warning
====================================================
This script quickly tests if the warning appears for a bad query.
"""

import json
from src.retrieval.hybrid import HybridSearch

print("Loading articles...")
articles = []
with open('data/processed/articles_all.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 50:  # Only 50 articles for quick test
            break
        articles.append(json.loads(line))

print(f"Loaded {len(articles)} articles\n")
print("Initializing Hybrid Search...")
hybrid = HybridSearch(articles)

print("\n" + "="*80)
print("TEST: Searching with gibberish query (SHOULD SHOW WARNING)")
print("="*80)
print("Query: 'zzzxxx qqq nonsense random gibberish'\n")

results = hybrid.search("zzzxxx qqq nonsense random gibberish", k=3)

print(f"\n✓ Top result score: {results[0][1]:.3f}")
print(f"✓ If you saw a warning message above, the feature is working!\n")
