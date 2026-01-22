import json
from collections import Counter

def find_top_none():
    idx_path = "data/processed/entity_index_linked.json"
    with open(idx_path, 'r', encoding='utf-8') as f:
        idx = json.load(f)
    
    # Entities with NO name (Neither English nor Bangla)
    orphans = []
    for k, v in idx.items():
        if not v.get('canonical_en') and not v.get('canonical_bn'):
            orphans.append((k, v.get('total_mentions', 0), v))
    
    orphans.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Total entities with NO name: {len(orphans)}")
    print("\nTop 20 orphans (no names):")
    for i, (eid, mentions, data) in enumerate(orphans[:20]):
        # Also print aliases if any
        aliases = data.get('aliases', []) + data.get('aliases_bn', [])
        print(f"{i+1}. ID: {eid} | Mentions: {mentions} | Aliases: {aliases[:5]}")

if __name__ == "__main__":
    find_top_none()
