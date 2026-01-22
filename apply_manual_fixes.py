"""
Apply Manual Entity Fixes (Improved)
Reads the manually edited entity_index_linked.json and:
1. Detects implicit merges (multiple IDs sharing the same canonical name)
2. RECOVERS ORPHANS: Finds IDs in articles that are missing from the index
3. Maps orphans to active IDs if their names in articles match
4. Unconditionally standardizes 'named_entities' -> 'entities'
5. Rebuilds the graph
"""

import json
import logging
from pathlib import Path
from collections import defaultdict, Counter
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_fixes():
    index_path = Path("data/processed/entity_index_linked.json")
    articles_path = Path("data/processed/articles_enhanced.jsonl")
    
    # Backup files before modifying
    shutil.copy(index_path, str(index_path) + ".bak")
    shutil.copy(articles_path, str(articles_path) + ".bak")
    logger.info("Backed up index and articles files.")

    # 1. Load Index
    logger.info(f"Loading index from {index_path}...")
    with open(index_path, 'r', encoding='utf-8') as f:
        entity_index = json.load(f)
    
    # 2. Identify Orphans (IDs in articles but not in index)
    logger.info("Scanning articles for orphaned IDs...")
    orphan_mentions = defaultdict(Counter)
    total_articles = 0
    with open(articles_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_articles += 1
            article = json.loads(line)
            # Check both keys
            e_list = article.get('entities', []) + article.get('named_entities', [])
            for ent in e_list:
                eid = ent.get('entity_id')
                if eid and eid not in entity_index:
                    orphan_mentions[eid][ent.get('text')] += 1
    
    logger.info(f"Found {len(orphan_mentions)} orphaned IDs across {total_articles} articles.")
    
    # 3. Build Name-to-ID lookup for recovery
    name_to_id = {}
    for eid, data in entity_index.items():
        if data.get('canonical_en'):
            name_to_id[data['canonical_en'].lower().strip()] = eid
        if data.get('canonical_bn'):
            name_to_id[data['canonical_bn'].strip()] = eid
        for alias in data.get('aliases', []):
            name_to_id[alias.lower().strip()] = eid
        for alias in data.get('aliases_bn', []):
            name_to_id[alias.strip()] = eid

    # 4. Map Orphans to Active IDs
    id_map = {}
    recovered_count = 0
    for eid, names in orphan_mentions.items():
        # Get most common name
        common_name = names.most_common(1)[0][0]
        search_name = common_name.lower().strip() if common_name else ""
        
        if search_name in name_to_id:
            target_id = name_to_id[search_name]
            id_map[eid] = target_id
            recovered_count += 1
            logger.info(f"Recovered orphan {eid} ({common_name}) -> mapped to {target_id} ({entity_index[target_id].get('canonical_en')})")
        else:
            # Could not recover, will remain "None" in graph unless manual mapping added
            pass

    # 5. Find Duplicates / Implicit Merges in Index
    bn_map = defaultdict(list)
    en_map = defaultdict(list)
    
    for eid, data in entity_index.items():
        if data.get('canonical_en'):
            en_map[data['canonical_en'].lower().strip()].append(eid)
        if data.get('canonical_bn'):
            bn_map[data['canonical_bn'].strip()].append(eid)
            
    def merge_group(ids):
        if len(ids) < 2: return
        def score(eid):
            e = entity_index[eid]
            return (1 if e.get('canonical_en') else 0, -int(eid[1:]))
        
        sorted_ids = sorted(ids, key=score, reverse=True)
        target_id = sorted_ids[0]
        for src_id in sorted_ids[1:]:
            if src_id in id_map: continue
            src = entity_index[src_id]
            logger.info(f"Merging duplicates {src_id} -> {target_id}")
            
            target = entity_index[target_id]
            target['aliases'] = list(set(target.get('aliases', []) + src.get('aliases', [])))
            target['total_mentions'] = target.get('total_mentions', 0) + src.get('total_mentions', 0)
            id_map[src_id] = target_id
            del entity_index[src_id]

    for ids in bn_map.values(): merge_group([i for i in ids if i not in id_map])
    for ids in en_map.values(): merge_group([i for i in ids if i not in id_map])
        
    logger.info(f"Total entries in id_map: {len(id_map)} ({recovered_count} recovered orphans)")
    
    # 6. Save Cleaned Index
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(entity_index, f, ensure_ascii=False, indent=2)
    
    # 7. Update Articles (Key migration + ID mapping)
    updated_articles = []
    articles_changed = False
    with open(articles_path, 'r', encoding='utf-8') as f:
        for line in f:
            article = json.loads(line)
            has_updates = False
            
            # Key migration
            if 'named_entities' in article:
                if 'entities' not in article:
                    article['entities'] = article['named_entities']
                else:
                    article['entities'].extend(article['named_entities'])
                del article['named_entities']
                has_updates = True

            # Update ID list
            if 'entity_ids' in article:
                new_ids = []
                for eid in article['entity_ids']:
                    if eid in id_map:
                        new_ids.append(id_map[eid])
                        has_updates = True
                    elif eid in entity_index:
                        new_ids.append(eid)
                final_ids = sorted(list(set(new_ids)))
                if final_ids != article.get('entity_ids'):
                    article['entity_ids'] = final_ids
                    has_updates = True
            
            # Update inline entities
            if 'entities' in article:
                for ent in article['entities']:
                    orig_id = ent.get('entity_id')
                    if orig_id in id_map:
                        ent['entity_id'] = id_map[orig_id]
                        has_updates = True
                        
            if has_updates: articles_changed = True
            updated_articles.append(article)
    
    if articles_changed:
        with open(articles_path, 'w', encoding='utf-8') as f:
            for art in updated_articles:
                f.write(json.dumps(art, ensure_ascii=False) + '\n')
        logger.info("Updated articles file.")

if __name__ == "__main__":
    apply_fixes()
