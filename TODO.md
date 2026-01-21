# What's Done vs What's Left

## ✅ DONE (Module A)
- 5,062 articles crawled (2,525 English, 2,537 Bangla) 
- All metadata present: title, body, url, date, language, tokens, entities
- Data at: `notebooks/data/articles_with_ner.jsonl`

## ❌ TODO (Priority Order)

### 1. Query Processing (Module B) - 4 hours
- [ ] Language detection
- [ ] Query translation (English ↔ Bangla)
- [ ] Optional: Query expansion (synonyms)

### 2. Finish Retrieval (Module C) - 2 hours  
- [ ] Normalize scores to [0-1]
- [ ] Add confidence scoring
- [ ] Test all 4 methods

### 3. Evaluation (Module D) - 4 hours
- [ ] Implement: Precision@10, Recall@50, nDCG, MRR
- [ ] Label 10 test queries
- [ ] Run evaluation script

### 4. Error Analysis - 2 hours
- [ ] Find 5 failure cases
- [ ] Document: translation fails, entity mismatches, cross-script issues

### 5. Report (Module E) - 3 hours
- [ ] Lit review (3-5 papers)
- [ ] Methodology summary
- [ ] Results tables
- [ ] AI usage log

**Total: ~15 hours**
