#!/usr/bin/env python3
"""
Quick test of the hybrid search fix for gibberish queries
"""

import json
from src.retrieval.hybrid import HybridSearch

# Load small set of articles
print("Loading 50 articles...")
articles = []
with open('data/processed/articles_all.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 50:
            break
        articles.append(json.loads(line))

print(f"Loaded {len(articles)} articles\n")

# Initialize hybrid search
print("Initializing Hybrid Search...")
hybrid = HybridSearch(articles)

# Test 1: Good query
print("\n" + "="*80)
print("TEST 1: Good Query")
print("="*80)
results = hybrid.search("Bangladesh cricket", k=3, verbose=False)
print(f"Top score: {results[0][1]:.3f} (Expected: > 0.20)")

# Test 2: Gibberish query  
print("\n" + "="*80)
print("TEST 2: Gibberish Query")
print("="*80)
results = hybrid.search("xyzqwerty blahblah random nonsense", k=3, verbose=False)
print(f"Top score: {results[0][1]:.3f} (Expected: < 0.20)")

# Test 3: Unrelated query
print("\n" + "="*80)
print("TEST 3: Unrelated Query")
print("="*80)
results = hybrid.search("quantum mechanics algorithm", k=3, verbose=False)
print(f"Top score: {results[0][1]:.3f} (Expected: < 0.20)")

print("\n" + "="*80)
print("✅ If gibberish/unrelated queries show scores < 0.20, the fix works!")
print("="*80)
