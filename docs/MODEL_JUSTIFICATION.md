# Module C: Retrieval Model Justification & Analysis

This document provides technical justification for the retrieval models implemented in CLIR-ly and analyzes the strengths and failures of each approach.

## Model 1: Lexical Retrieval (BM25 vs TF-IDF)

### Why BM25 was chosen:
- **Term Saturation**: In TF-IDF, a term's score increases linearly with frequency. In BM25, the score reaches a "saturation point" (controlled by `k1`), preventing a single word from dominating a score simply by appearing dozens of times in a long document.
- **Length Normalization**: BM25 adjusts scores based on document length (controlled by `b`). It ensures that shorter documents aren't unfairly penalized for having lower raw term counts.
- ** MESSY DATA**: BM25 is more robust to the "noisy" nature of news scrapes where Boilerplate text might repeat common keywords.
### Benchmark Results (`scripts/compare_lexical.py`):
| Query | BM25 | TF-IDF | CLIR-ly (Our System) |
| :--- | :--- | :--- | :--- |
| **"শেখ হাসিনা"** | ❌ No Results | ❌ No Results | ✅ **Found Relevant EN Articles** |
| **"BNP সংবাদ"** | ✅ Exact Match | ✅ Exact Match | ✅ **Expanded Contextual Match** |

**Conclusion**: While BM25 is a better lexical starting point than TF-IDF, our KG-integrated expansion is the only method that successfully bridges the "Script Gap."

### Failure Analysis of Lexical Models:
- **Zero Synonyms**: If the query is "Economic crisis" but the article uses "Financial downturn," lexical models find **zero matches**.
- **Paraphrasing**: Lexical models cannot handle rephrased content (e.g., "The weather in Dhaka is hot" vs "Dhaka is experiencing high temperatures").
- **No Cross-Script Support**: Without manual mapping or translation, "Dhaka" will NEVER match "ঢাকা".

## Model 2: Fuzzy & Transliteration Matching

### Technical Implementation:
- **Levenshtein Distance**: Handles typos (e.g., "Banlgadesh" -> "Bangladesh").
- **Character N-grams**: Vital for transliteration. By breaking "Dhaka" into `dha`, `hak`, `aka`, we can match variants that sound similar but are spelled slightly differently in English.

### Justification:
Fuzzy matching acts as the "safety net" for user input errors and the inevitable naming variations found in scraped news titles.

## Model 3: Semantic Matching (LaBSE)

### Why LaBSE?
- **Cross-Lingual by Design**: LaBSE was specifically trained to align meanings across 100+ languages including Bangla and English.
- **Concept Awareness**: It understands that "Cyclone" and "Natural Disaster" are semantically adjacent, even if they share no characters.

### Failure Cases:
- **Entity Specificity**: Semantic models can sometimes be "too fuzzy." A search for "Sheikh Hasina" might return articles about "Khaleda Zia" simply because they share the same political context (Semantic similarity).

## Advanced Strategy: Knowledge Graph & Cross-Lingual Linkage

To overcome the inherent limitations of both lexical and semantic models, we implemented a structured Knowledge Graph (KG) that acts as a deterministic bridge between languages.

### 1. Cross-Lingual Linking (1,573 mapped pairs)
- **Hybrid Linking**: Combined manual seed links with LLM-powered normalization and LaBSE-based semantic matching.
- **Structure**: Each entity node in our graph contains canonical forms for both English and Bangla, plus common aliases.

### 2. EBQE (Entity-Based Query Expansion)
- When a user enters a query, our system identifies entities and automatically injects their cross-lingual counterparts into the search parameters.
- **Result**: A search for "শেখ হাসিনা" doesn't just rely on a translation model; it pulls strictly verified mappings from our index, ensuring 100% accuracy for critical proper nouns.

### 3. "Pinned" Translations
- We bypass Neural Machine Translation (NMT) errors for known entities. Regular NMT models often fail on local names or acronyms (e.g., mis-translating a politician's name into a generic noun). Our "Pinning" strategy ensures the canonical indexed name is always used.

## Model 4: Hybrid Ranking (The Solution)

### The Balanced Approach:
We use a weighted combination (`alpha=0.2, beta=0.6, gamma=0.2`) to get the "best of all worlds":
1. **Semantic (60%)**: Handles the core cross-lingual concept.
2. **BM25 (20%)**: Re-ranks results to favor exact keyword matches (fixing Semantic's lack of specificity).
3. **Fuzzy (20%)**: Ensures typos don't break the whole pipeline.

### Conclusion:
The hybrid approach ensures that a search for "Dhaka" retrieves articles about "ঢাকা" (Semantic) while also ensuring that an article actually mentioning the word "Dhaka" in the title ranks higher (BM25).
