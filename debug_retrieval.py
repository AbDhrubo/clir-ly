"""Debug: Why Bangla documents aren't being returned."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.bm25 import BM25Search

# Load a mix of docs
docs = []
with open('data/processed/articles_enhanced.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    stride = len(lines) // 1000
    for i in range(0, len(lines), stride):
        if len(docs) >= 1000: break
        docs.append(json.loads(lines[i]))

# Check distribution in sample
en_sample = sum(1 for d in docs if not any('\u0980' <= c <= '\u09FF' for c in d.get('body','')[:100]))
bn_sample = len(docs) - en_sample
print(f"Sample Distribution: EN={en_sample}, BN={bn_sample}")

# Initialize BM25
bm25 = BM25Search(docs)

# Test Bangla-only query
print("\n--- Test 1: Pure Bangla Query ---")
bn_query = "বাংলাদেশ"
results = bm25.search(bn_query, k=5)
for i, (doc_id, score, doc) in enumerate(results, 1):
    has_bn = any('\u0980' <= c <= '\u09FF' for c in doc.get('body','')[:100])
    lang = "BN" if has_bn else "EN"
    print(f"  {i}. [{score:.3f}] ({lang}) {doc['title'][:50]}")

# Test English-only query
print("\n--- Test 2: Pure English Query ---")
en_query = "Bangladesh"
results = bm25.search(en_query, k=5)
for i, (doc_id, score, doc) in enumerate(results, 1):
    has_bn = any('\u0980' <= c <= '\u09FF' for c in doc.get('body','')[:100])
    lang = "BN" if has_bn else "EN"
    print(f"  {i}. [{score:.3f}] ({lang}) {doc['title'][:50]}")

# Test combined query (our EBQE approach)
print("\n--- Test 3: Combined Query (EBQE) ---")
combined_query = "Bangladesh বাংলাদেশ"
results = bm25.search(combined_query, k=5)
for i, (doc_id, score, doc) in enumerate(results, 1):
    has_bn = any('\u0980' <= c <= '\u09FF' for c in doc.get('body','')[:100])
    lang = "BN" if has_bn else "EN"
    print(f"  {i}. [{score:.3f}] ({lang}) {doc['title'][:50]}")
