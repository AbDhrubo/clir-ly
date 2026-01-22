# CLIR-LY Project: Complete Session History

## Project Overview
**Cross-Lingual Information Retrieval (CLIR) for Bangla-English News**

Built a complete pipeline for crawling, processing, and linking news articles from 10 Bangladeshi news sources in both English and Bangla, with the goal of enabling cross-lingual search and retrieval.

**Repository**: `d:\GitHub\clir-ly`
**Session Dates**: January 18-21, 2026

---

## Phase 1: Multi-Source News Crawling

### 1.1 English News Sites (5 sources)

| Site | URL Pattern | Method |
|------|-------------|--------|
| Daily Star | `thedailystar.net` | BeautifulSoup |
| New Age | `newagebd.net` | BeautifulSoup |
| Dhaka Tribune | `dhakatribune.com` | BeautifulSoup |
| Daily Sun | `daily-sun.com` | BeautifulSoup |
| New Nation | `thenewnation.net` | BeautifulSoup |

### 1.2 Bangla News Sites (5 sources)

| Site | URL Pattern | Method |
|------|-------------|--------|
| Prothom Alo | `prothomalo.com` | API + Selenium |
| BD News 24 | `bangla.bdnews24.com` | BeautifulSoup |
| Kaler Kantho | `kalerkantho.com` | BeautifulSoup |
| Bangla Tribune | `banglatribune.com` | BeautifulSoup |
| Dhaka Post | `dhakapost.com` | BeautifulSoup |

### 1.3 Crawling Challenges & Solutions

**Challenge 1: Cloudflare Protection**
- Some sites blocked requests with standard User-Agent
- Solution: Used `cloudscraper` library to bypass protection

**Challenge 2: Dynamic Content (Prothom Alo)**
- Prothom Alo uses JavaScript rendering
- Solution: Used Selenium with headless Chrome, then discovered their internal API

**Challenge 3: Rate Limiting**
- Aggressive crawling triggered IP blocks
- Solution: Implemented exponential backoff, 2-second delays between requests

### 1.4 Final Crawl Stats

```
Total Articles: 5,062
├── English: 2,525 (49.9%)
└── Bangla: 2,537 (50.1%)

By Source:
├── Daily Star: ~500
├── New Age: ~500
├── Dhaka Tribune: ~500
├── Daily Sun: ~500
├── New Nation: ~500
├── Prothom Alo: ~500
├── BD News 24: ~500
├── Kaler Kantho: ~500
├── Bangla Tribune: ~500
└── Dhaka Post: ~500
```

---

## Phase 2: Named Entity Recognition (NER)

### 2.1 Model Selection

**English NER**: `Jean-Baptiste/roberta-large-ner-english`
- F1 Score: 97.5%
- Entity Types: PERSON, ORG, LOC, MISC

**Bangla NER**: `sagorsarker/mbert-bengali-ner`
- Based on multilingual BERT
- Fine-tuned on Bangla NER dataset
- Entity Types: PER, ORG, LOC, MISC

### 2.2 GPU Acceleration

Used DirectML for AMD GPU support:
```python
import torch_directml
device = torch_directml.device()
model.to(device)
```

Hardware: AMD RX 6600 XT (8GB VRAM)

### 2.3 NER Pipeline Code

```python
# English NER
from transformers import pipeline
en_ner = pipeline("ner", model="Jean-Baptiste/roberta-large-ner-english", 
                  aggregation_strategy="simple", device=device)

# Bangla NER
bn_ner = pipeline("ner", model="sagorsarker/mbert-bengali-ner",
                  aggregation_strategy="simple", device=device)

# Process article
entities = en_ner(article['content']) if lang == 'en' else bn_ner(article['content'])
```

### 2.4 NER Output Stats

```
Total Entities Extracted: 82,150
├── English: 40,000+ entities
└── Bangla: 42,000+ entities

Entity Type Distribution:
├── PERSON: ~28,000 (34%)
├── ORG: ~24,000 (29%)
├── LOC: ~20,000 (24%)
└── MISC: ~10,000 (12%)
```

### 2.5 Bangla NER Debugging

Encountered issues with Bangla entity extraction:
- **Problem**: mBERT was extracting single characters
- **Solution**: Adjusted tokenization and used word-level aggregation
- **Problem**: Broken Unicode in Bangla text
- **Solution**: Normalized Unicode to NFC form before processing

---

## Phase 3: Entity Enhancement

### 3.1 Entity Deduplication (Fuzzy Clustering)

Used fuzzy string matching to cluster similar entities:

```python
from rapidfuzz import fuzz

def cluster_entities(entities, threshold=85):
    clusters = []
    for entity in entities:
        matched = False
        for cluster in clusters:
            if fuzz.ratio(entity, cluster[0]) >= threshold:
                cluster.append(entity)
                matched = True
                break
        if not matched:
            clusters.append([entity])
    return clusters
```

**Result**: 34,375 unique → 26,410 canonical entities

### 3.2 LLM-Based Entity Normalization

#### 3.2.1 First Attempt: Gemini

- Used Gemini for entity cleaning
- **Issue**: Gemini returned inconsistent JSON format

#### 3.2.2 Switch to OpenAI

- Switched to `gpt-4o-mini` (later `gpt-5-mini`)
- Used `response_format={"type": "json_object"}` for consistent output

#### 3.2.3 LLM Prompt

```python
prompt = """
You are an expert data cleaner. Map raw entities to canonical forms.
Fix broken Bangla spellings (e.g. 'চটটগরাম' -> 'চট্টগ্রাম').
Return JSON { "raw_string": {"en": "...", "bn": "...", "type": "..."} }.
"""
```

#### 3.2.4 Batch Processing

```python
BATCH_SIZE = 100
MAX_CONCURRENT = 5  # 5 parallel requests

# Async batch processing
async def process_all(limit=50000):
    batches = [entities[i:i+BATCH_SIZE] for i in range(0, len(entities), BATCH_SIZE)]
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    async def run_batch(batch):
        async with sem:
            return await clean_batch(batch)
    
    results = await asyncio.gather(*[run_batch(b) for b in batches])
```

#### 3.2.5 Overnight Run Stats

```
Total Entities Processed: 34,374
Batches: 334
Time: ~5 hours
LLM Mappings Generated: 1,822
API Calls: 334 (with retries)
```

### 3.3 Cross-Lingual Entity Linking

#### 3.3.1 Seed Links (29 initial)

Manual seed links from the EntityNormalizer:
```python
SEED_LINKS = {
    'Bangladesh': 'বাংলাদেশ',
    'Dhaka': 'ঢাকা',
    'India': 'ভারত',
    # ...
}
```

#### 3.3.2 LLM Crosslinker (320 links)

Created `llm_crosslinker.py` to use LLM mappings directly:

**Phase 1: Exact Matching**
- Normalized English lookup (case-insensitive)
- Exact Bangla lookup

**Phase 2: LaBSE Fuzzy Matching**
- When exact Bangla match fails, use LaBSE embeddings
- Find most similar Bangla entity in index
- Threshold: 0.85 cosine similarity

```python
# Fuzzy Bangla matching with LaBSE
bn_embeddings = model.encode(bn_texts)  # 11,935 Bangla entities
llm_bn_embeddings = model.encode(unmatched_bn)  # 683 unmatched LLM forms

for i, (en_id, en, llm_bn) in enumerate(unmatched_bn):
    sims = np.dot(bn_embeddings, llm_bn_embeddings[i])
    best_idx = np.argmax(sims)
    if sims[best_idx] >= 0.85:
        llm_links.append((en_id, bn_list[best_idx][1], en, llm_bn))
```

#### 3.3.3 LaBSE Semantic Matching (1,280 links)

Used sentence-transformers/LaBSE for cross-lingual semantic similarity:

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/LaBSE')

# Embed English and Bangla entities
en_embeddings = model.encode(en_entities)
bn_embeddings = model.encode(bn_entities)

# Compute similarity matrix
similarity_matrix = np.dot(en_embeddings, bn_embeddings.T)

# Find matches above threshold
matches = np.where(similarity_matrix >= 0.75)
```

#### 3.3.4 Final Cross-Linking Stats

```
Seed Links: 29
LLM Crosslinker Links: 320
├── Phase 1 (Exact): 193
└── Phase 2 (LaBSE Fuzzy): 127
LaBSE Semantic Links: 1,280
─────────────────────────────
Total Cross-Linked Pairs: 1,573
```

---

## Phase 4: Knowledge Graph Construction

### 4.1 Graph Building Algorithm

```python
# Co-occurrence based edge creation
for article in articles:
    entities_in_article = article['entity_ids']
    for i, ent1 in enumerate(entities_in_article):
        for ent2 in entities_in_article[i+1:]:
            # Add edge (or increment weight)
            if G.has_edge(ent1, ent2):
                G[ent1][ent2]['weight'] += 1
            else:
                G.add_edge(ent1, ent2, weight=1)
```

### 4.2 Graph Statistics

```
Nodes: 25,586
Edges: 66,267
Average Degree: 5.18
Max Degree: 2,534 (Bangladesh)
Connected Components: 18,259
Largest Component: 7,292 nodes (28.5%)
```

### 4.3 Top Connected Entities

| Rank | Entity | Type | Degree |
|------|--------|------|--------|
| 1 | Bangladesh | LOC | 2,534 |
| 2 | Dhaka | LOC | 2,463 |
| 3 | US | LOC | 780 |
| 4 | India | LOC | 671 |
| 5 | Jatiya (জাতীয়) | ORG | 664 |
| 6 | Rahman (রহমান) | PERSON | 657 |
| 7 | Islam (ইসলাম) | PERSON | 608 |
| 8 | Upazila (উপজেলা) | LOC | 594 |

### 4.4 Export Formats

- **GEXF**: For Gephi visualization
- **JSON**: For D3.js/web visualization
- **HTML**: Interactive PyVis visualization

---

## Phase 5: Issues Encountered & Solutions

### 5.1 LLM Map Not Updating

**Problem**: `id_map.json` wasn't saving new LLM results
**Diagnosis**: Created `debug_llm_response.py` to test LLM output
**Solution**: Added debug logging, found cache was being read but not merged correctly

### 5.2 Cross-Links Barely Moving

**Problem**: Processed 34K entities but cross-links only went from 1,406 → 1,413
**Root Cause**: LLM map had both EN/BN forms but we only used them for normalization, not linking
**Solution**: Created `llm_crosslinker.py` to directly create links from LLM map

### 5.3 Bangla Matching Bottleneck

**Problem**: Only 241/1239 (19%) overlap between LLM Bangla forms and index Bangla
**Root Cause**: LLM outputs normalized Bangla, index has raw extracted text with variations
**Solution**: Added LaBSE fuzzy matching for Bangla (Phase 2 in crosslinker)

### 5.4 Pipeline Output Overwriting

**Problem**: LaBSE was loading from `entity_index.json`, overwriting LLM crosslinker output
**Solution**: Changed LLM crosslinker to output to `entity_index_llm_linked.json`, LaBSE reads from there


## Final Metrics Summary

| Metric | Value |
|--------|-------|
| News Sources | 10 |
| Articles Crawled | 5,062 |
| Raw Entities Extracted | 82,150 |
| Canonical Entities | 25,586 |
| LLM Mappings (id_map.json) | 1,822 |
| Cross-Linked Entity Pairs | 1,573 |
| Knowledge Graph Nodes | 25,586 |
| Knowledge Graph Edges | 66,267 |
| Largest Connected Component | 7,292 nodes |
| Processing Time (LLM) | ~5 hours |
| Total Session Duration | ~3 days |

---

*Generated: January 21, 2026*
