"""
Module C - TF-IDF Search Implementation
=======================================
This file implements the classic TF-IDF (Term Frequency-Inverse Document Frequency) algorithm.
Used for comparison with BM25.

What does TF-IDF do?
- Measures importance of a word to a document in a collection.
- TF (Term Frequency): How many times word appears in a document.
- IDF (Inverse Document Frequency): How rare the word is across all documents.
"""

import math
from collections import Counter, defaultdict

class TFIDFSearch:
    """Classic TF-IDF Search Implementation."""
    
    def __init__(self, documents):
        self.documents = documents
        self.inverted_index = self._build_inverted_index()
        self.idf_scores = self._calculate_idf()
        print(f"✅ TF-IDF initialized with {len(documents)} documents")

    def _tokenize(self, text):
        if not text: return []
        return text.lower().split()

    def _build_inverted_index(self):
        index = defaultdict(lambda: defaultdict(int))
        for doc_id, doc in enumerate(self.documents):
            text = (doc.get('title', '') + ' ' + doc.get('body', '')).strip()
            words = self._tokenize(text)
            word_counts = Counter(words)
            for word, count in word_counts.items():
                index[word][doc_id] = count
        return index

    def _calculate_idf(self):
        idf = {}
        N = len(self.documents)
        for word, docs in self.inverted_index.items():
            df = len(docs)
            # Classic IDF: log(N/df)
            idf[word] = math.log(N / (df + 1)) + 1
        return idf

    def search(self, query, k=10):
        query_words = self._tokenize(query)
        if not query_words: return []
        
        doc_scores = defaultdict(float)
        for word in query_words:
            if word in self.inverted_index:
                idf = self.idf_scores.get(word, 0)
                for doc_id, tf in self.inverted_index[word].items():
                    # TF-IDF calculation
                    # Using log normalization for TF to prevent saturation
                    tf_score = 1 + math.log(tf) if tf > 0 else 0
                    doc_scores[doc_id] += tf_score * idf
        
        results = []
        for doc_id, score in doc_scores.items():
            results.append((doc_id, score, self.documents[doc_id]))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

if __name__ == "__main__":
    sample_docs = [{"title": "test", "body": "hello world"}, {"title": "world", "body": "hello universe"}]
    tfidf = TFIDFSearch(sample_docs)
    print(tfidf.search("hello"))
