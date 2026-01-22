"""
Verify Query Processor with EBQE and Pinned Translations
"""

import logging
from src.query.processor import QueryProcessor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_queries():
    processor = QueryProcessor()
    
    queries = [
        "Dhaka news",
        "Prothom Alo headline",
        "বিএনপি সংবাদ",
        "Bangladesh results",
        "শেখ হাসিনা"
    ]
    
    print("\n" + "="*60)
    print("QUERY PROCESSOR VERIFICATION (EBQE + PINNED)")
    print("="*60)
    
    for q in queries:
        print(f"\nOriginal: {q}")
        result = processor.process(q)
        print(f"Language: {result['language']}")
        print(f"Normalized: {result['normalized']}")
        print(f"Translated: {result['translated']}")
        print(f"Expanded EN: {result['expanded_en']}")
        print(f"Expanded BN: {result['expanded_bn']}")
        
    print("\n" + "="*60)

if __name__ == "__main__":
    test_queries()
