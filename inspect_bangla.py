"""
Inspect Bangla Entities
Check for broken entities and subword artifacts.
"""

import json
from collections import Counter

def inspect_bangla_entities():
    print("Scanning for Bangla entities...")
    entities = Counter()
    
    with open('notebooks/data/articles_with_ner.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            article = json.loads(line)
            if article.get('language') != 'bn':
                continue
                
            for ent in article.get('named_entities', []):
                text = ent.get('text', '')
                entities[text] += 1

    print(f"\nTotal unique Bangla entities: {len(entities)}")
    
    print("\nTop 50 Most Frequent Bangla Entities:")
    print("-" * 40)
    for text, count in entities.most_common(50):
        print(f"{count:<5} | {text}")
        
    print("\nEntities containing '##' (Subwords):")
    print("-" * 40)
    subwords = [(t, c) for t, c in entities.items() if '##' in t]
    for text, count in sorted(subwords, key=lambda x: -x[1])[:20]:
        print(f"{count:<5} | {text}")

    print("\nSingle character entities:")
    print("-" * 40)
    singles = [(t, c) for t, c in entities.items() if len(t) == 1]
    for text, count in sorted(singles, key=lambda x: -x[1])[:20]:
        print(f"{count:<5} | {text}")

if __name__ == "__main__":
    inspect_bangla_entities()
