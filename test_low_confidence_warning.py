#!/usr/bin/env python3
"""
Test Low-Confidence Warning Feature
===================================
This script tests whether the low-confidence warning appears for poor queries.

Test cases:
1. Good query (high confidence) - should NOT show warning
2. Random gibberish query (low confidence) - should show warning
3. Completely unrelated query (low confidence) - should show warning
"""

import json
from src.retrieval.hybrid import HybridSearch


def load_articles(limit=100):
    """Load a subset of articles for testing"""
    articles = []
    with open('data/processed/articles_all.jsonl', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break
            articles.append(json.loads(line))
    return articles


def test_low_confidence():
    """Test the low-confidence warning feature"""
    
    print("="*80)
    print("TESTING LOW-CONFIDENCE WARNING FEATURE")
    print("="*80)
    print("\nLoading articles...")
    
    # Load articles
    articles = load_articles(limit=100)
    print(f"Loaded {len(articles)} articles for testing\n")
    
    # Initialize hybrid search
    print("Initializing Hybrid Search...")
    hybrid = HybridSearch(articles)
    
    # Test Case 1: Good query (should NOT show warning)
    print("\n" + "="*80)
    print("TEST CASE 1: Good Query (Expected: NO WARNING)")
    print("="*80)
    print("Query: 'Bangladesh cricket team'")
    results = hybrid.search("Bangladesh cricket team", k=5, verbose=False)
    print(f"✓ Top result score: {results[0][1]:.3f}")
    print(f"  Title: {results[0][2].get('title', 'N/A')[:80]}")
    
    # Test Case 2: Gibberish query (should show warning)
    print("\n" + "="*80)
    print("TEST CASE 2: Gibberish Query (Expected: WARNING)")
    print("="*80)
    print("Query: 'xyzqwerty asdfzxcv blahblah random'")
    results = hybrid.search("xyzqwerty asdfzxcv blahblah random", k=5, verbose=False)
    print(f"✓ Top result score: {results[0][1]:.3f}")
    
    # Test Case 3: Unrelated query (should show warning)
    print("\n" + "="*80)
    print("TEST CASE 3: Completely Unrelated Query (Expected: WARNING)")
    print("="*80)
    print("Query: 'quantum mechanics photosynthesis algorithm'")
    results = hybrid.search("quantum mechanics photosynthesis algorithm", k=5, verbose=False)
    print(f"✓ Top result score: {results[0][1]:.3f}")
    
    # Test Case 4: Custom threshold (should show warning even for moderate score)
    print("\n" + "="*80)
    print("TEST CASE 4: Custom Threshold 0.50 (Expected: WARNING if score < 0.50)")
    print("="*80)
    print("Query: 'Bangladesh'")
    results = hybrid.search("Bangladesh", k=5, verbose=False, confidence_threshold=0.50)
    print(f"✓ Top result score: {results[0][1]:.3f}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED")
    print("="*80)
    print("\nSummary:")
    print("- If you saw warnings for Test Cases 2 and 3, the feature is working!")
    print("- Test Case 1 should NOT show a warning")
    print("- Test Case 4 may or may not show warning depending on the score")


if __name__ == "__main__":
    test_low_confidence()
