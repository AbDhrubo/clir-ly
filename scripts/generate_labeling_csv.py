#!/usr/bin/env python3
"""
Generate Labeling CSV Helper
============================
Creates a CSV file with search results ready for manual labeling.

Usage:
    python scripts/generate_labeling_csv.py
"""

import json
import csv
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.retrieval.hybrid import HybridSearch


# Define test queries (customize these!)
TEST_QUERIES = [
    {"query": "Bangladesh politics", "language": "en"},
    {"query": "cricket team performance", "language": "en"},
    {"query": "ঢাকায় শিক্ষা", "language": "bn"},
    {"query": "অর্থনীতি সংবাদ", "language": "bn"},
    {"query": "climate change Bangladesh", "language": "en"},
    # Add more queries here as needed
]


def load_articles(limit=None):
    """Load articles from processed data."""
    print("Loading articles...")
    articles = []
    with open('data/processed/articles_all.jsonl', 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            articles.append(json.loads(line))
    
    print(f"✅ Loaded {len(articles)} articles")
    return articles


def generate_labeling_csv(output_path='data/labeled_queries_DRAFT.csv', k=50):
    """
    Generate CSV with search results ready for labeling.
    
    Args:
        output_path: Where to save the CSV
        k: Number of top results per query
    """
    print("\n" + "="*80)
    print("LABELING CSV GENERATOR")
    print("="*80)
    
    # Load articles
    articles = load_articles()
    
    # Initialize hybrid search
    print("\nInitializing Hybrid Search...")
    hybrid = HybridSearch(articles)
    
    # Prepare CSV
    Path(output_path).parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'query', 'doc_url', 'language', 'relevant', 'annotator',
            'title', 'score', 'rank'
        ])
        writer.writeheader()
        
        # Process each query
        for query_info in TEST_QUERIES:
            query = query_info['query']
            language = query_info['language']
            
            print(f"\n🔍 Searching: '{query}' ({language})")
            
            # Run search
            results = hybrid.search(query, k=k, verbose=False)
            
            print(f"   Found {len(results)} results")
            
            # Write results to CSV
            for rank, (doc_id, score, doc, breakdown) in enumerate(results, 1):
                writer.writerow({
                    'query': query,
                    'doc_url': doc.get('url', ''),
                    'language': language,
                    'relevant': '',  # TO BE FILLED BY YOU!
                    'annotator': '',  # TO BE FILLED BY YOU!
                    'title': doc.get('title', ''),
                    'score': f"{score:.3f}",
                    'rank': rank
                })
    
    print("\n" + "="*80)
    print("DRAFT CSV GENERATED!")
    print("="*80)
    print(f"\n📄 File: {output_path}")
    print(f"\n✏️  Next Steps:")
    print("   1. Open the CSV file")
    print("   2. For each row, fill in the 'relevant' column:")
    print("      - 'yes' if the document is relevant to the query")
    print("      - 'no' if the document is NOT relevant")
    print("   3. Fill in 'annotator' with your name")
    print("   4. Save as 'data/labeled_queries.csv'")
    print("   5. Run: python scripts/run_evaluation.py")
    
    print("\n💡 Labeling Tips:")
    print("   • Review the title - is it on-topic?")
    print("   • Be consistent across all queries")
    print("   • Not all results will be relevant!")
    print("   • Aim for at least 20-50 labels per query")
    
    print(f"\n⏱️  Estimated time: ~2 hours for {len(TEST_QUERIES)} queries")


def main():
    """Main function."""
    print("\n" + "="*80)
    print("This script helps you prepare data for evaluation.")
    print("="*80)
    
    print("\nQueries to be searched:")
    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"  {i}. {q['query']} ({q['language']})")
    
    print(f"\n📝 Will generate top 50 results for each query")
    print(f"   Total labels needed: {len(TEST_QUERIES) * 50}")
    
    response = input("\nProceed? (y/n): ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        return
    
    generate_labeling_csv()
    
    print("\n✅ Done! Ready for manual labeling.")


if __name__ == "__main__":
    main()
