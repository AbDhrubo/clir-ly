"""Test Bangla NER model directly"""
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch_directml

# Sample Bangla text from the articles
sample_text = """আগামী ১২ ফেব্রুয়ারি অনুষ্ঠিত হতে যাচ্ছে ত্রয়োদশ জাতীয় সংসদ নির্বাচন। 
শেখ হাসিনা ঢাকায় বক্তৃতা দিয়েছেন। বাংলাদেশ জাতীয়তাবাদী দল (বিএনপি) এবং আওয়ামী লীগ নির্বাচনে অংশ নিচ্ছে।"""

print("Loading Bangla NER model...")
model_name = "sagorsarker/mbert-bengali-ner"
device = torch_directml.device()
print(f"Using device: {device}")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForTokenClassification.from_pretrained(model_name)

# Try on CPU first
print("\n=== Testing on CPU ===")
ner_pipeline_cpu = pipeline("ner", model=model, tokenizer=tokenizer, device=-1, aggregation_strategy="simple")
results_cpu = ner_pipeline_cpu(sample_text)
print(f"CPU Results: {results_cpu}")

# Try on DirectML 
print("\n=== Testing on DirectML ===")
try:
    ner_pipeline_dml = pipeline("ner", model=model, tokenizer=tokenizer, device=device, aggregation_strategy="simple")
    results_dml = ner_pipeline_dml(sample_text)
    print(f"DirectML Results: {results_dml}")
except Exception as e:
    print(f"DirectML Error: {e}")

# Check model labels
print(f"\nModel labels: {model.config.id2label}")
