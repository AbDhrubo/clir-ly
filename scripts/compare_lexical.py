"""
Lexical Comparison: BM25 vs TF-IDF
==================================
This script compares BM25 and TF-IDF models on the news dataset.
It helps fulfill Model 1 requirements of Module C.
"""

import sys
import json
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval.bm25 import BM25Search
from src.retrieval.tfidf import TFIDFSearch
from src.query.processor import QueryProcessor

def load_data():
    path = project_root / "data" / "processed" / "articles_enhanced.jsonl"
    docs = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= 1000: break # Use subset for speed
            docs.append(json.loads(line))
    return docs

def compare():
    docs = load_data()
    print(f"Loaded {len(docs)} articles for comparison.")
    
    bm25 = BM25Search(docs)
    tfidf = TFIDFSearch(docs)
    query_proc = QueryProcessor()
    
    test_queries = [
        "Dhaka news",
        "Prothom Alo",
        "BNP সংবাদ",
        "Bangladesh results",
        "শেখ হাসিনা"
    ]
    
    print("\n" + "="*80)
    print(f"{'Query':<25} | {'Model':<10} | {'Top Result Title'}")
    print("-" * 80)
    
    for q in test_queries:
        # 1. Raw BM25
        b_res = bm25.search(q, k=1)
        b_title = b_res[0][2]['title'][:40] if b_res else "No results"
        print(f"{q:<25} | {'BM25':<10} | {b_title}")
        
        # 2. Raw TF-IDF
        t_res = tfidf.search(q, k=1)
        t_title = t_res[0][2]['title'][:40] if t_res else "No results"
        print(f"{'':<25} | {'TF-IDF':<10} | {t_title}")

        # 3. Our System (EBQE + KG Integration)
        # Process query through our pipeline
        proc_q = query_proc.process(q)
        # Search using BOTH expanded versions (CLIR-ly approach)
        # We'll combine the results from expanded_en and expanded_bn
        combined_q = f"{proc_q['expanded_en']} {proc_q['expanded_bn']}"
        kg_res = bm25.search(combined_q, k=1)
        kg_title = kg_res[0][2]['title'][:40] if kg_res else "No results"
        print(f"{'':<25} | {'CLIR-ly':<10} | {kg_title}")
        print("-" * 80)

if __name__ == "__main__":
    compare()
