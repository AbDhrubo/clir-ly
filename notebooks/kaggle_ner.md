# CLIR-ly NER Processing on Kaggle

This notebook runs Named Entity Recognition on the collected news articles.

## Setup

```python
# Install dependencies
!pip install spacy transformers torch tqdm -q
!python -m spacy download en_core_web_trf -q

# Clone repo or upload files
# Option 1: Upload articles_all.jsonl to Kaggle dataset
# Option 2: Clone repo
# !git clone https://github.com/YOUR_USER/clir-ly.git
```

## Run NER

```python
import sys
sys.path.append('/kaggle/working/clir-ly/src/preprocessing')
# Or if you uploaded the files directly:
# sys.path.append('/kaggle/working')

from run_ner import run_ner_pipeline

# Run with GPU
results = run_ner_pipeline(
    input_path='/kaggle/input/clir-articles/articles_all.jsonl',
    output_path='/kaggle/working/articles_with_ner.jsonl',
    use_gpu=True,
    bn_confidence=0.5  # Conservative threshold
)

print(f"Extracted {results['total_entities']} entities!")
```

## Quick Test (Single Article)

```python
from ner_extractor import NERProcessor

processor = NERProcessor(use_gpu=True)

# Test English
en_text = "Sheikh Hasina met with Joe Biden in Washington DC yesterday."
entities = processor.extract_entities(en_text, "en")
print("English entities:", entities)

# Test Bangla  
bn_text = "শেখ হাসিনা ঢাকায় বাংলাদেশ ব্যাংকে গিয়েছিলেন।"
entities = processor.extract_entities(bn_text, "bn")
print("Bangla entities:", entities)
```

## Download Results

```python
from IPython.display import FileLink
FileLink('/kaggle/working/articles_with_ner.jsonl')
```

## Expected Output Schema

```json
{
  "url": "https://...",
  "title": "Article Title",
  "body": "Article content...",
  "named_entities": [
    {"text": "Sheikh Hasina", "label": "PERSON", "start": 0, "end": 13},
    {"text": "Bangladesh", "label": "GPE", "start": 45, "end": 55}
  ]
}
```

## Entity Types

### English (spaCy)
- PERSON, ORG, GPE (countries/cities), LOC (locations)
- DATE, TIME, MONEY, PERCENT, QUANTITY
- NORP (nationalities/groups), FAC (buildings), EVENT, etc.

### Bangla (mBERT)
- PERSON, ORG, LOC
