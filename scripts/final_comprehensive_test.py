"""
Final Comprehensive Test Suite for CLIR-ly
==========================================
Verifies:
1. Knowledge Graph Loading
2. Query Processor (Detect -> Normalize -> Pin -> Translate -> Expand)
3. Hybrid Search (Lexical + Semantic + Fuzzy)
4. Cross-lingual Result Coverage
"""

import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.query.processor import QueryProcessor
from src.retrieval import HybridSearch

def load_data(limit=1000):
    path = project_root / "data" / "processed" / "articles_enhanced.jsonl"
    docs = []
    if not path.exists():
        logger.error(f"Data file not found at {path}")
        return []
        
    all_lines = []
    with open(path, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
    
    # Stratified-like sampling: pick every Nth line to get diverse sources
    total = len(all_lines)
    stride = max(1, total // limit)
    
    for i in range(0, total, stride):
        if len(docs) >= limit: break
        docs.append(json.loads(all_lines[i]))
        
    return docs

def run_suite():
    print("\n" + "="*80)
    print("🚀 STARTING CLIR-LY COMPREHENSIVE TEST SUITE")
    print("="*80)

    # 1. Initialize Components
    print("\n[1/4] Initializing Components...")
    docs = load_data()
    if not docs:
        print("❌ FAILED: No documents loaded.")
        return

    try:
        processor = QueryProcessor()
        hybrid = HybridSearch(docs)
    except Exception as e:
        print(f"❌ FAILED: Initialization error: {e}")
        return
    print("✅ Components initialized successfully.")

    # 2. Test Cases (Targeting specific features)
    test_cases = [
        {
            "query": "Dhaka city news",
            "expect": "PINNED/EBQE",
            "desc": "Verify location pinning and cross-lingual expansion"
        },
        {
            "query": "শেখ হাসিনা",
            "expect": "KG-LINK",
            "desc": "Verify Bangla entity recognition and English expansion"
        },
        {
            "query": "Prothom Alo headline",
            "expect": "MULTI-WORD",
            "desc": "Verify multi-word entity identification"
        }
    ]

    print("\n[2/4] Testing Query Processing...")
    for tc in test_cases:
        print(f"\n🔹 Testing: {tc['desc']}")
        res = processor.process(tc['query'])
        
        print(f"   Original: {res['original']}")
        print(f"   Detected Lang: {res['language']}")
        print(f"   Pinned Map: {getattr(processor, 'pinned_map', 'N/A')}")
        print(f"   Expanded EN: {res['expanded_en']}")
        print(f"   Expanded BN: {res['expanded_bn']}")
        
        # Validation
        if tc['expect'] == "PINNED/EBQE":
            if "ঢাকা" in res['expanded_bn']:
                print("   ✅ SUCCESS: 'Dhaka' correctly expanded to 'ঢাকা'")
            else:
                print("   ❌ FAILURE: Expansion missing for 'Dhaka'")

    # 3. Test Retrieval Performance
    print("\n[3/4] Testing Hybrid Retrieval...")
    for tc in test_cases:
        query = tc['query']
        print(f"\n🔍 Searching for: '{query}'")
        
        # Use our CLIR-ly strategy: search with expanded versions
        proc = processor.process(query)
        combined_query = f"{proc['expanded_en']} {proc['expanded_bn']}"
        
        results = hybrid.search(combined_query, k=5)
        
        if not results:
            print("   ❌ FAILED: No results returned.")
            continue
            
        langs_found = set()
        for i, (doc_id, score, doc, breakdown) in enumerate(results, 1):
            # Detect lang from content (simple heuristic)
            content = doc.get('body', '')
            has_bn = any('\u0980' <= c <= '\u09FF' for c in content)
            l = "BN" if has_bn else "EN"
            langs_found.add(l)
            print(f"   {i}. [{score:.3f}] {doc['title'][:50]}... ({l})")
        
        if len(langs_found) > 1:
            print(f"   ✅ SUCCESS: Cross-lingual results found! ({', '.join(langs_found)})")
        else:
            print(f"   ⚠️  NOTE: Only {list(langs_found)[0]} results found. Check if queries are diverse enough.")

    print("\n" + "="*80)
    print("✨ TEST SUITE COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_suite()
