#!/usr/bin/env python3
"""
QUICK DEMO: Cross-Lingual BM25 Search
Shows how queries in ONE language return results in BOTH languages
"""

import json
from pathlib import Path

# Load first few documents to show structure
data_path = Path("notebooks/data/articles_with_ner.jsonl")

print("\n" + "="*70)
print("CROSS-LINGUAL SEARCH DEMO")
print("="*70 + "\n")

print("Sample Documents (first 5):\n")
with open(data_path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 5:
            break
        doc = json.loads(line)
        lang = "EN" if doc['language'] == 'en' else "BN"
        print(f"[{i+1}] {lang} | Title: {doc['title'][:60]}")

print("\n" + "-"*70)
print("\nExample: Search for 'Bangladesh politics'")
print("-"*70 + "\n")

print("PROCESS:")
print("  1. User enters: 'Bangladesh politics' (English)")
print("  2. Module B translates: 'বাংলাদেশের রাজনীতি' (Bangla)")
print("  3. BM25 searches:")
print("     - Search 1: 'Bangladesh politics' on ENGLISH documents")
print("     - Search 2: 'বাংলাদেশের রাজনীতি' on BANGLA documents")
print("  4. Results merged and sorted by relevance score")
print("\n")

print("EXPECTED RESULT (10 docs):")
print("  Rank | Score | Language | Title")
print("  -----|-------|----------|--------")
print("  1    | 0.94  | EN       | Political parties in Bangladesh...")
print("  2    | 0.89  | BN       | বাংলাদেশের নির্বাচন প্রক্রিয়া...")
print("  3    | 0.87  | BN       | সরকার ও বিরোধী দল...")
print("  4    | 0.85  | EN       | Elections in South Asia...")
print("  5    | 0.81  | BN       | রাজনৈতিক সংকট...")
print("  ... (5 more)")

print("\n" + "-"*70)
print("KEY INSIGHT")
print("-"*70 + "\n")

print("Single query in ONE language returns results in BOTH languages!")
print("\n✓ English speaker gets Bangla results (translated)")
print("✓ Bangla speaker gets English results (translated)")
print("✓ Mixed audiences get complete coverage\n")

print("="*70)
print("\nRun the actual test on Colab:")
print("  !python scripts/test_bm25_simple.py\n")
print("="*70 + "\n")
