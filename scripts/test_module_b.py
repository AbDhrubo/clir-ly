"""Test Module B - Query Processing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.query.processor import process_query


def test_query_processing():
    """Test the query pipeline."""
    
    print("=" * 60)
    print("MODULE B - Query Processing Tests")
    print("=" * 60)
    
    test_queries = [
        "Bangladesh politics",                    # English
        "বাংলাদেশের রাজনীতি",                    # Bangla
        "Amir Khan actor",                        # English
        "আমির খান অভিনেতা",                      # Bangla
        "education in dhaka",                     # English
        "ঢাকায় শিক্ষা ব্যবস্থা",                  # Bangla
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: {query}")
        try:
            result = process_query(query)
            print(f"   Language: {result['language']}")
            print(f"   Normalized: {result['normalized']}")
            print(f"   Translated: {result['translated']}")
            print(f"   Mixed language: {result['is_mixed']}")
            print("   ✅ OK")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_query_processing()
