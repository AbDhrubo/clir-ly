"""
Search Demo - Interactive Retrieval System
==========================================
This script demonstrates all search methods using the crawled article data.

What this program does:
1. Loads articles from data/processed/
2. Initializes all search methods (BM25, Fuzzy, Semantic, Hybrid)
3. Runs example queries to show how each method works
4. Compares results from different methods

Usage:
    python scripts/search_demo.py
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
        # Default to the processed articles
        filepath = project_root / 'data' / 'processed' / 'articles_all.jsonl'
    else:
        filepath = Path(filepath)
    
    print(f"📂 Loading documents from {filepath}...")
    
    try:
        documents = []
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    documents.append(json.loads(line))
        
        print(f"✅ Loaded {len(documents)} documents")
        return documents
    
    except FileNotFoundError:
        print(f"❌ Error: File {filepath} not found!")
        print("   Please make sure articles data is in data/processed/")
        return []
    
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {filepath}")
        print(f"   {e}")
        return []


def print_results(results, method_name, max_display=5):
    """
    Pretty print search results
    
    Args:
        results: List of tuples [(doc_id, score, document), ...]
        method_name: Name of the search method (for display)
        max_display: Maximum number of results to display
    """
    print(f"\n{'='*70}")
    print(f"📊 {method_name} Results")
    print(f"{'='*70}")
    
    if not results:
        print("   No results found.")
        return
    
    for i, item in enumerate(results[:max_display], 1):
        # Handle both 3-tuple and 4-tuple results
        if len(item) == 4:
            doc_id, score, doc, breakdown = item
        else:
            doc_id, score, doc = item
            breakdown = None
        
        title = doc.get('title', 'No Title')
        category = doc.get('category', 'N/A')
        
        # Truncate body for display
        body = doc.get('body', '')
        body_preview = body[:100] + '...' if len(body) > 100 else body
        
        print(f"\n{i}. Score: {score:.4f}")
        print(f"   Title: {title}")
        print(f"   Category: {category}")
        print(f"   Preview: {body_preview}")
        
        # Print breakdown if available (from hybrid search)
        if breakdown:
            print(f"   Score Breakdown:")
            print(f"     • BM25:     {breakdown['bm25']:.4f}")
            print(f"     • Fuzzy:    {breakdown['fuzzy']:.4f}")
            print(f"     • Semantic: {breakdown['semantic']:.4f}")


def compare_methods(query, bm25, fuzzy, semantic, hybrid, k=3):
    """
    Compare results from all search methods for a single query
    
    Args:
        query: Search query string
        bm25: BM25Search instance
        fuzzy: FuzzySearch instance
        semantic: SemanticSearch instance
        hybrid: HybridSearch instance
        k: Number of results to show for each method
    """
    print(f"\n\n{'#'*70}")
    print(f"# QUERY: '{query}'")
    print(f"{'#'*70}")
    
    # Run all four methods
    print_results(bm25.search(query, k), "BM25 (Keyword Matching)", k)
    print_results(fuzzy.search(query, k), "Fuzzy (Typo Handling)", k)
    print_results(semantic.search(query, k), "Semantic (Meaning Understanding)", k)
    print_results(hybrid.search(query, k), "Hybrid (Combined)", k)


def main():
    """
    Main function to run the search demo
    """
    print("\n" + "="*70)
    print("SEARCH DEMO: Information Retrieval Methods")
    print("="*70)
    print()
    
    # Step 1: Load documents
    documents = load_documents()
    
    if not documents:
        print("\n❌ Cannot proceed without documents. Exiting.")
        return
    
    print(f"\n📝 Document Statistics:")
    print(f"   Total documents: {len(documents)}")
    
    # Count languages
    languages = {}
    for doc in documents:
        lang = doc.get('language', 'unknown')
        languages[lang] = languages.get(lang, 0) + 1
    
    for lang, count in languages.items():
        print(f"   {lang}: {count} documents")
    
    # Step 2: Initialize all search methods
    print(f"\n{'='*70}")
    print("Initializing Search Methods...")
    print(f"{'='*70}\n")
    
    print("Initializing BM25 Search...")
    bm25 = BM25Search(documents)
    
    print("\nInitializing Fuzzy Search...")
    fuzzy = FuzzySearch(documents, threshold=70)
    
    print("\nInitializing Semantic Search...")
    semantic = SemanticSearch(documents)
    
    print("\nInitializing Hybrid Search...")
    hybrid = HybridSearch(documents, alpha=0.2, beta=0.6, gamma=0.2)
    
    # Step 3: Run example queries
    print(f"\n{'='*70}")
    print("Running Example Queries")
    print(f"{'='*70}")
    
    # Test queries - mix of Bangla and English
    test_queries = [
        "আমির খান",                    # Bangla: Aamir Khan
        "cricket Bangladesh",          # English: cricket
        "নির্বাচন",                     # Bangla: election
        "ঢাকা শহর",                     # Bangla: Dhaka city
        "Aamir Khan actor",            # English query for Bangla content
    ]
    
    # Run comparisons for each test query
    for query in test_queries:
        compare_methods(query, bm25, fuzzy, semantic, hybrid, k=3)
    
    # Step 4: Interactive mode (optional)
    print(f"\n\n{'='*70}")
    print("Interactive Search Mode")
    print(f"{'='*70}")
    print("Enter your own queries to test the search system.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            user_query = input("🔍 Enter search query: ").strip()
            
            if user_query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for using the search demo! Goodbye!")
                break
            
            if not user_query:
                print("   Please enter a valid query.\n")
                continue
            
            # Show hybrid search results (best overall method)
            print(f"\n{'='*70}")
            print(f"Searching for: '{user_query}'")
            print(f"{'='*70}")
            
            results = hybrid.search(user_query, k=5, verbose=True)
            
        except KeyboardInterrupt:
            print("\n\n👋 Search interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Please try again.\n")


if __name__ == "__main__":
    # Run the main program
    main()
