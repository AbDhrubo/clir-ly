import json

# Check Bangla articles
bn_articles = []
en_articles = []

with open('notebooks/data/articles_with_ner.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        article = json.loads(line)
        if article.get('language') == 'bn':
            bn_articles.append(article)
        else:
            en_articles.append(article)

print(f"English articles: {len(en_articles)}")
print(f"Bangla articles: {len(bn_articles)}")

# Check entities
en_entities = sum(len(a.get('named_entities', [])) for a in en_articles)
bn_entities = sum(len(a.get('named_entities', [])) for a in bn_articles)

print(f"\nEnglish entities: {en_entities}")
print(f"Bangla entities: {bn_entities}")

# Sample Bangla article
if bn_articles:
    sample = bn_articles[0]
    print(f"\n=== Sample Bangla Article ===")
    print(f"Source: {sample.get('source')}")
    print(f"Body (first 300 chars): {sample.get('body', '')[:300]}")
    print(f"Entities: {sample.get('named_entities', [])}")
