"""
Method Comparison Tool
======================
This script helps you understand the differences between search methods
by running the same query through all methods and showing detailed comparisons.

Use this to:
1. Understand which method works best for different query types
2. See how each method scores documents
3. Prepare examples for your presentation

Usage:
    python scripts/compare_retrieval.py
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval import BM25Search, FuzzySearch, SemanticSearch, HybridSearch


def load_documents(filepath=None):
    """
    Load documents from JSONL file
    
    Args:
        filepath: Path to the JSONL file containing articles
                  If None, tries to load from data/processed/articles_all.jsonl
        
    Returns:
        List of document dictionaries
    """
    if filepath is None:
        filepath = project_root / 'data' / 'processed' / 'articles_all.jsonl'
    else:
        filepath = Path(filepath)
    
    documents = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                documents.append(json.loads(line))
    
    return documents


def compare_single_query(query, bm25, fuzzy, semantic, hybrid, k=5):
    """
    Run a single query through all methods and show detailed comparison
    """
    print("\n" + "="*80)
    print(f"QUERY: '{query}'")
    print("="*80)
    
    # Get results from each method
    bm25_results = bm25.search(query, k=k)
    fuzzy_results = fuzzy.search(query, k=k)
    semantic_results = semantic.search(query, k=k)
    hybrid_results = hybrid.search(query, k=k)
    
    # Collect all unique documents
    all_doc_ids = set()
    
    for doc_id, _, _ in bm25_results:
        all_doc_ids.add(doc_id)
    for doc_id, _, _ in fuzzy_results:
        all_doc_ids.add(doc_id)
    for doc_id, _, _ in semantic_results:
        all_doc_ids.add(doc_id)
    for doc_id, _, _, _ in hybrid_results:
        all_doc_ids.add(doc_id)
    
    # Create score lookup for each method
    bm25_scores = {doc_id: score for doc_id, score, _ in bm25_results}
    fuzzy_scores = {doc_id: score for doc_id, score, _ in fuzzy_results}
    semantic_scores = {doc_id: score for doc_id, score, _ in semantic_results}
    hybrid_scores = {doc_id: score for doc_id, score, _, _ in hybrid_results}
    
    # Print comparison table header
    print(f"\n{'Document':<40} {'BM25':>10} {'Fuzzy':>10} {'Semantic':>10} {'Hybrid':>10}")
    print("-" * 80)
    
    # Print top documents from hybrid (best overall)
    for doc_id, score, doc, breakdown in hybrid_results:
        title = doc.get('title', 'N/A')[:38]  # Truncate long titles
        
        bm25_score = bm25_scores.get(doc_id, 0.0)
        fuzzy_score = fuzzy_scores.get(doc_id, 0.0)
        semantic_score = semantic_scores.get(doc_id, 0.0)
        hybrid_score = score
        
        print(f"{title:<40} {bm25_score:>10.4f} {fuzzy_score:>10.4f} "
              f"{semantic_score:>10.4f} {hybrid_score:>10.4f}")
    
    print("\n" + "-" * 80)
    
    # Analysis
    print("\n📊 Analysis:")
    
    # Which method found the most results?
    print(f"\nResults found:")
    print(f"  • BM25:     {len(bm25_results)} documents")
    print(f"  • Fuzzy:    {len(fuzzy_results)} documents")
    print(f"  • Semantic: {len(semantic_results)} documents")
    print(f"  • Hybrid:   {len(hybrid_results)} documents (combination)")
    
    # Which method gave the highest score to top result?
    if hybrid_results:
        top_doc_id = hybrid_results[0][0]
        print(f"\nTop result scores for: '{hybrid_results[0][2]['title']}'")
        print(f"  • BM25:     {bm25_scores.get(top_doc_id, 0.0):.4f}")
        print(f"  • Fuzzy:    {fuzzy_scores.get(top_doc_id, 0.0):.4f}")
        print(f"  • Semantic: {semantic_scores.get(top_doc_id, 0.0):.4f}")
        print(f"  • Hybrid:   {hybrid_results[0][1]:.4f}")
        
        # Show breakdown
        breakdown = hybrid_results[0][3]
        print(f"\nHybrid breakdown:")
        print(f"  • BM25 contribution:     {breakdown['bm25']:.4f} × 0.2 = {breakdown['bm25']*0.2:.4f}")
        print(f"  • Fuzzy contribution:    {breakdown['fuzzy']:.4f} × 0.2 = {breakdown['fuzzy']*0.2:.4f}")
        print(f"  • Semantic contribution: {breakdown['semantic']:.4f} × 0.6 = {breakdown['semantic']*0.6:.4f}")


def main():
    """
    Main comparison tool
    """
    print("\n" + "="*80)
    print("SEARCH METHOD COMPARISON TOOL")
    print("="*80)
    
    # Load documents
    print("\nLoading documents...")
    documents = load_documents()
    print(f"✅ Loaded {len(documents)} documents\n")
    
    # Initialize all methods
    print("Initializing search methods...\n")
    bm25 = BM25Search(documents)
    fuzzy = FuzzySearch(documents, threshold=70)
    semantic = SemanticSearch(documents)
    hybrid = HybridSearch(documents, alpha=0.2, beta=0.6, gamma=0.2)
    
    # Predefined test cases with explanations
    test_cases = [
        {
            "query": "আমির খান",
            "description": "Exact Bangla keyword - BM25 should excel",
        },
        {
            "query": "Aamir Khan actor",
            "description": "English query for Bangla content - Semantic should excel",
        },
        {
            "query": "crickt Bangladesh",
            "description": "Query with typo - Fuzzy should help",
        },
        {
            "query": "নির্বাচন কমিশন",
            "description": "Bangla political terms - All methods should work",
        },
        {
            "query": "capital city",
            "description": "Conceptual query - Semantic should find Dhaka articles",
        },
    ]
    
    # Run each test case
    for i, test_case in enumerate(test_cases, 1):
        print("\n\n" + "#"*80)
        print(f"# Test Case {i}: {test_case['description']}")
        print("#"*80)
        
        compare_single_query(
            test_case['query'],
            bm25, fuzzy, semantic, hybrid,
            k=5
        )
    
    # Interactive mode
    print("\n\n" + "="*80)
    print("INTERACTIVE MODE")
    print("="*80)
    print("Enter your own queries to compare methods.")
    print("Type 'quit' to exit.\n")
    
    while True:
        try:
            query = input("🔍 Enter query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not query:
                continue
            
            compare_single_query(query, bm25, fuzzy, semantic, hybrid, k=5)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break


if __name__ == "__main__":
    main()
