"""
LLM Entity Cleaner (Async)
Uses OpenAI API to fix broken entities (Parrallel processing).
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
from collections import Counter
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MODEL_NAME = "gpt-5-mini"
BATCH_SIZE = 100
MAX_CONCURRENT = 5  # 5 batches at a time

def get_entities_to_clean(limit: int = 5000, reverse: bool = False) -> List[Tuple[str, int]]:
    """Get entities sorted by frequency.
    
    Args:
        limit: Maximum number of entities to return
        reverse: If True, get LEAST common (bottom) entities first
    """
    logger.info(f"Scanning for entities (reverse={reverse})...")
    entities = Counter()
    
    with open('notebooks/data/articles_with_ner.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            article = json.loads(line)
            for ent in article.get('named_entities', []):
                text = ent.get('text', '').strip()
                if len(text) > 1:
                    entities[text] += 1
    
    logger.info(f"Found {len(entities)} unique raw entities")
    valid = []
    # Sort by frequency (ascending if reverse, descending otherwise)
    sorted_entities = entities.most_common() if not reverse else sorted(entities.items(), key=lambda x: x[1])
    for text, count in sorted_entities:
        if text.isdigit() or len(text) > 50: continue
        valid.append((text, count))
    return valid[:limit]

async def clean_batch(batch_id: int, entities: List[str]) -> Dict[str, Dict]:
    """Clean a single batch asynchronously."""
    prompt = """
    You are an expert data cleaner. Map raw entities to canonical forms.
    Fix broken Bangla spellings (e.g. 'চটটগরাম' -> 'চট্টগ্রাম').
    Return JSON { "raw": {"en": "...", "bn": "...", "type": "..."} }.
    """
    user_content = f"Entities: {json.dumps(entities, ensure_ascii=False)}"

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Batch {batch_id} failed: {e}")
        return {}

async def process_all(limit: int = 3000, reverse: bool = False):
    # 1. Get data (bottom entities if reverse=True)
    entities = get_entities_to_clean(limit, reverse=reverse)
    raw_texts = [x[0] for x in entities]
    
    # 2. Check cache
    cache_path = Path("data/processed/id_map.json")
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            cleaned_map = json.load(f)
    else:
        cleaned_map = {}
        
    to_process = [t for t in raw_texts if t not in cleaned_map]
    logger.info(f"Processing {len(to_process)} new entities in batches of {BATCH_SIZE}...")
    
    # 3. Queue batches
    batches = [to_process[i:i+BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def run_batch(i, batch):
        async with sem:
            logger.info(f"Starting batch {i+1}/{len(batches)}")
            res = await clean_batch(i, batch)
            return res

    tasks = [run_batch(i, b) for i, b in enumerate(batches)]
    results = await asyncio.gather(*tasks)
    
    # 4. Merge results
    new_count = 0
    for res in results:
        for raw, info in res.items():
            if isinstance(info, dict):
                cleaned_map[raw] = info
                new_count += 1
                
    logger.info(f"Merged {new_count} new mappings.")
    
    # 5. Save
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(cleaned_map, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(cleaned_map)} mappings to {cache_path}")

if __name__ == "__main__":
    # Process ALL entities (cache will skip already-done ones)
    asyncio.run(process_all(limit=50000, reverse=False))
