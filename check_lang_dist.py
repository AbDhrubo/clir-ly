"""Quick diagnostic to check language distribution."""
import json

en_count = 0
bn_count = 0

with open('data/processed/articles_enhanced.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        doc = json.loads(line)
        body = doc.get('body', '')[:200]
        has_bn = any('\u0980' <= c <= '\u09FF' for c in body)
        if has_bn:
            bn_count += 1
        else:
            en_count += 1

print(f"Total Articles: {en_count + bn_count}")
print(f"English: {en_count}")
print(f"Bangla: {bn_count}")
