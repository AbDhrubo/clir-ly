"""Debug: Check Semantic Search distribution."""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.semantic import SemanticSearch

# Load a mix of docs
docs = []
with open('data/processed/articles_enhanced.jsonl', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    stride = len(lines) // 500
    for i in range(0, len(lines), stride):
        if len(docs) >= 500: break
        docs.append(json.loads(lines[i]))

en_sample = sum(1 for d in docs if not any('\u0980' <= c <= '\u09FF' for c in d.get('body','')[:100]))
bn_sample = len(docs) - en_sample
print(f"Sample Distribution: EN={en_sample}, BN={bn_sample}")

# Initialize Semantic
semantic = SemanticSearch(docs)

# Test combined query
print("\n--- Semantic Search: Combined Query ---")
combined_query = "Bangladesh বাংলাদেশ"
results = semantic.search(combined_query, k=10)
en_found = 0
bn_found = 0
for i, (doc_id, score, doc) in enumerate(results, 1):
    has_bn = any('\u0980' <= c <= '\u09FF' for c in doc.get('body','')[:100])
    lang = "BN" if has_bn else "EN"
    if has_bn: bn_found += 1
    else: en_found += 1
    print(f"  {i}. [{score:.3f}] ({lang}) {doc['title'][:50]}")
print(f"\nResult Distribution: EN={en_found}, BN={bn_found}")
