"""
Named Entity Recognition and cross-lingual mapping
Without spaCy - uses regex and dictionaries
"""

import re
from typing import List, Dict, Optional
from collections import defaultdict

class NERMapper:
    """
    Extracts and maps named entities between Bangla and English
    Without spaCy dependency
    """
    
    def __init__(self):
        # Entity mapping dictionary (expanded)
        self.entity_mapping = {
            'LOC': {  # Locations
                'en': {
                    'Dhaka': 'ঢাকা',
                    'Bangladesh': 'বাংলাদেশ',
                    'Chittagong': 'চট্টগ্রাম',
                    'Khulna': 'খুলনা',
                    'Rajshahi': 'রাজশাহী',
                    'Sylhet': 'সিলেট',
                    'Barisal': 'বরিশাল',
                    'Rangpur': 'রংপুর',
                    'New York': 'নিউইয়র্ক',
                    'London': 'লন্ডন',
                    'Delhi': 'দিল্লি',
                    'Kolkata': 'কলকাতা',
                    'India': 'ভারত',
                    'United States': 'যুক্তরাষ্ট্র',
                    'USA': 'যুক্তরাষ্ট্র',
                    'America': 'আমেরিকা',
                    'UK': 'যুক্তরাজ্য',
                    'China': 'চীন',
                },
                'bn': {
                    'ঢাকা': 'Dhaka',
                    'বাংলাদেশ': 'Bangladesh',
                    'চট্টগ্রাম': 'Chittagong',
                    'খুলনা': 'Khulna',
                    'রাজশাহী': 'Rajshahi',
                    'সিলেট': 'Sylhet',
                    'বরিশাল': 'Barisal',
                    'রংপুর': 'Rangpur',
                    'নিউইয়র্ক': 'New York',
                    'লন্ডন': 'London',
                    'দিল্লি': 'Delhi',
                    'কলকাতা': 'Kolkata',
                    'ভারত': 'India',
                    'যুক্তরাষ্ট্র': 'United States',
                    'আমেরিকা': 'America',
                    'যুক্তরাজ্য': 'UK',
                    'চীন': 'China',
                }
            },
            'ORG': {  # Organizations
                'en': {
                    'UN': 'জাতিসংঘ',
                    'United Nations': 'জাতিসংঘ',
                    'WHO': 'বিশ্ব স্বাস্থ্য সংস্থা',
                    'World Health Organization': 'বিশ্ব স্বাস্থ্য সংস্থা',
                    'IMF': 'আন্তর্জাতিক মুদ্রা তহবিল',
                    'World Bank': 'বিশ্ব ব্যাংক',
                    'BBC': 'বিবিসি',
                    'CNN': 'সিএনএন',
                    'Reuters': 'রয়টার্স',
                    'Al Jazeera': 'আল জাজিরা',
                },
                'bn': {
                    'জাতিসংঘ': 'United Nations',
                    'বিশ্ব স্বাস্থ্য সংস্থা': 'World Health Organization',
                    'আন্তর্জাতিক মুদ্রা তহবিল': 'International Monetary Fund',
                    'বিশ্ব ব্যাংক': 'World Bank',
                    'বিবিসি': 'BBC',
                    'সিএনএন': 'CNN',
                    'রয়টার্স': 'Reuters',
                    'আল জাজিরা': 'Al Jazeera',
                }
            },
            'PERSON': {  # People
                'en': {
                    'Sheikh Hasina': 'শেখ হাসিনা',
                    'Hasina': 'হাসিনা',
                    'Khaleda Zia': 'খালেদা জিয়া',
                    'Zia': 'জিয়া',
                    'Modi': 'মোদি',
                    'Narendra Modi': 'নরেন্দ্র মোদি',
                    'Biden': 'বাইডেন',
                    'Joe Biden': 'জো বাইডেন',
                    'Trump': 'ট্রাম্প',
                    'Donald Trump': 'ডোনাল্ড ট্রাম্প',
                    'Putin': 'পুতিন',
                    'Vladimir Putin': 'ভ্লাদিমির পুতিন',
                },
                'bn': {
                    'শেখ হাসিনা': 'Sheikh Hasina',
                    'হাসিনা': 'Hasina',
                    'খালেদা জিয়া': 'Khaleda Zia',
                    'জিয়া': 'Zia',
                    'মোদি': 'Modi',
                    'নরেন্দ্র মোদি': 'Narendra Modi',
                    'বাইডেন': 'Biden',
                    'জো বাইডেন': 'Joe Biden',
                    'ট্রাম্প': 'Trump',
                    'ডোনাল্ড ট্রাম্প': 'Donald Trump',
                    'পুতিন': 'Putin',
                    'ভ্লাদিমির পুতিন': 'Vladimir Putin',
                }
            },
            'MISC': {  # Miscellaneous
                'en': {
                    'COVID-19': 'কোভিড-১৯',
                    'Coronavirus': 'করোনাভাইরাস',
                    'GDP': 'জিডিপি',
                    'GDP growth': 'জিডিপি বৃদ্ধি',
                    'Inflation': 'মুদ্রাস্ফীতি',
                    'Budget': 'বাজেট',
                    'Election': 'নির্বাচন',
                    'Parliament': 'সংসদ',
                    'Government': 'সরকার',
                    'Economy': 'অর্থনীতি',
                },
                'bn': {
                    'কোভিড-১৯': 'COVID-19',
                    'করোনাভাইরাস': 'Coronavirus',
                    'জিডিপি': 'GDP',
                    'জিডিপি বৃদ্ধি': 'GDP growth',
                    'মুদ্রাস্ফীতি': 'Inflation',
                    'বাজেট': 'Budget',
                    'নির্বাচন': 'Election',
                    'সংসদ': 'Parliament',
                    'সরকার': 'Government',
                    'অর্থনীতি': 'Economy',
                }
            }
        }
        
        # Regex patterns for entity detection
        self.entity_patterns = {
            'en': {
                'PERSON': r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b',  # First Last names
                'LOC': r'\b(Dhaka|Bangladesh|Chittagong|Khulna|Rajshahi|Sylhet|New York|London|India|USA|UK)\b',
                'ORG': r'\b(UN|WHO|IMF|BBC|CNN|Reuters|World Bank)\b',
                'MISC': r'\b(COVID-19|Coronavirus|GDP|Inflation|Budget|Election)\b',
            },
            'bn': {
                'LOC': r'(ঢাকা|বাংলাদেশ|চট্টগ্রাম|খুলনা|রাজশাহী|সিলেট|ভারত|আমেরিকা|যুক্তরাষ্ট্র)',
                'PERSON': r'(শেখ হাসিনা|খালেদা জিয়া|মোদি|বাইডেন|ট্রাম্প|পুতিন)',
                'ORG': r'(জাতিসংঘ|বিশ্ব স্বাস্থ্য সংস্থা|আন্তর্জাতিক মুদ্রা তহবিল|বিশ্ব ব্যাংক|বিবিসি|সিএনএন)',
                'MISC': r'(কোভিড-১৯|করোনাভাইরাস|জিডিপি|মুদ্রাস্ফীতি|বাজেট|নির্বাচন|সংসদ|সরকার|অর্থনীতি)',
            }
        }
    
    def extract_entities(self, text: str, lang: str) -> List[Dict]:
        """
        Extract named entities from text using regex patterns
        """
        entities = []
        
        if lang not in ['en', 'bn']:
            return entities
        
        # Check for entities in mapping dictionaries first
        words = text.split()
        for word in words:
            for entity_type in ['LOC', 'ORG', 'PERSON', 'MISC']:
                if word in self.entity_mapping[entity_type][lang]:
                    entities.append({
                        'text': word,
                        'type': entity_type,
                        'mapped': self.entity_mapping[entity_type][lang][word]
                    })
        
        # Use regex patterns to find multi-word entities
        for entity_type, pattern in self.entity_patterns[lang].items():
            matches = re.finditer(pattern, text, re.IGNORECASE if lang == 'en' else 0)
            for match in matches:
                entity_text = match.group()
                # Check if we already found this entity
                if not any(e['text'] == entity_text for e in entities):
                    entities.append({
                        'text': entity_text,
                        'type': entity_type,
                        'start': match.start(),
                        'end': match.end(),
                        'mapped': self._map_entity(entity_text, entity_type, lang)
                    })
        
        # Remove duplicates
        unique_entities = []
        seen = set()
        for entity in entities:
            key = (entity['text'].lower() if lang == 'en' else entity['text'], entity['type'])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        return unique_entities
    
    def _map_entity(self, entity_text: str, entity_type: str, source_lang: str) -> Optional[str]:
        """
        Map entity to other language
        """
        if entity_type not in self.entity_mapping:
            return None
        
        mapping_dict = self.entity_mapping[entity_type]
        
        if source_lang == 'en':
            # Map from English to Bangla
            if entity_text in mapping_dict['en']:
                return mapping_dict['en'][entity_text]
            # Try case-insensitive
            if entity_text.lower() in {k.lower(): v for k, v in mapping_dict['en'].items()}:
                for key, value in mapping_dict['en'].items():
                    if key.lower() == entity_text.lower():
                        return value
        elif source_lang == 'bn':
            # Map from Bangla to English
            if entity_text in mapping_dict['bn']:
                return mapping_dict['bn'][entity_text]
        
        return None
    
    def map_query_entities(self, query: str, source_lang: str, target_lang: str) -> Dict:
        """
        Extract and map entities in query
        """
        entities = self.extract_entities(query, source_lang)
        
        # Create query variations with mapped entities
        mapped_queries = []
        if entities:
            # For each entity that has a mapping, create a version with mapped entity
            for entity in entities:
                if entity['mapped']:
                    # Replace entity with its mapped version
                    mapped_query = query.replace(entity['text'], entity['mapped'])
                    if mapped_query != query:
                        mapped_queries.append(mapped_query)
            
            # Also create a version with all entities mapped
            all_mapped_query = query
            for entity in entities:
                if entity['mapped']:
                    all_mapped_query = all_mapped_query.replace(entity['text'], entity['mapped'])
            if all_mapped_query != query:
                mapped_queries.append(all_mapped_query)
        
        return {
            'original_query': query,
            'source_lang': source_lang,
            'target_lang': target_lang,
            'entities': entities,
            'mapped_queries': mapped_queries,
            'has_entities': len(entities) > 0
        }