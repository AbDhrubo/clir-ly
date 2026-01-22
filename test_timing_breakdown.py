#!/usr/bin/env python3
"""
Test Query Execution Time Breakdown
===================================
Demonstrates the new timing feature in hybrid search.
"""

import json
from src.retrieval.hybrid import HybridSearch

# Load articles
print("Loading 100 articles...")
articles = []
with open('data/processed/articles_all.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 100:
            break
        articles.append(json.loads(line))

print(f"Loaded {len(articles)} articles\n")

# Initialize hybrid search
print("Initializing Hybrid Search...")
hybrid = HybridSearch(articles)

print("\n" + "="*80)
print("TEST: Query Execution Time Breakdown")
print("="*80)

# Test with timing
query = "Bangladesh cricket team"
print(f"\nQuery: '{query}'\n")

results, timing = hybrid.search(query, k=5, return_timing=True)

print(f"⏱️  Execution Time Breakdown:")
print(f"{'='*80}")
print(f"  BM25 Search:     {timing['bm25_ms']:>8.2f} ms  ({timing['bm25_ms']/timing['total_ms']*100:>5.1f}%)")
print(f"  Fuzzy Search:    {timing['fuzzy_ms']:>8.2f} ms  ({timing['fuzzy_ms']/timing['total_ms']*100:>5.1f}%)")
print(f"  Semantic Search: {timing['semantic_ms']:>8.2f} ms  ({timing['semantic_ms']/timing['total_ms']*100:>5.1f}%)")
print(f"  Ranking/Combine: {timing['ranking_ms']:>8.2f} ms  ({timing['ranking_ms']/timing['total_ms']*100:>5.1f}%)")
print(f"  {'─'*80}")
print(f"  Total Time:      {timing['total_ms']:>8.2f} ms")
print(f"{'='*80}")

print(f"\n📊 Top Result:")
print(f"  Score: {results[0][1]:.3f}")
print(f"  Title: {results[0][2].get('title', 'N/A')[:60]}")

print(f"\n✅ Timing breakdown feature working!")
print(f"\nNote: Semantic search is typically the slowest component.")
print(f"      BM25 and Fuzzy are much faster but less accurate for cross-lingual search.")
