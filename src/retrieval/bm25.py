"""
Module C - BM25 Search Implementation
=====================================
This file implements BM25 (Best Matching 25) algorithm for keyword-based search.

What does BM25 do?
- It finds documents that contain the query words
- It gives higher scores to important words that are rare in the collection
- It considers how often words appear in a document
- It normalizes by document length (so short documents aren't unfairly favored)

Simple Example:
Query: "আমির খান"
- BM25 will find documents containing "আমির" and "খান"
- Documents with both words score higher than documents with just one
- If "আমির খান" is rare in collection, it gets higher weight
"""

import math
from collections import Counter, defaultdict


class BM25Search:
    """
    BM25 Search Algorithm
    
    Parameters you can adjust:
    - k1: Controls how much term frequency matters (default: 1.5)
          Higher k1 = word frequency matters more
    - b: Controls document length normalization (default: 0.75)
         Higher b = longer documents get penalized more
    """
    
    def __init__(self, documents, k1=1.5, b=0.75):
        """
        Initialize BM25 with a collection of documents
        
        Args:
            documents: List of dictionaries with 'body' and 'title' fields
            k1: Term frequency saturation parameter (default: 1.5)
            b: Length normalization parameter (default: 0.75)
        """
        self.documents = documents
        self.k1 = k1
        self.b = b
        
        # Build the inverted index (word -> which documents contain it)
        self.inverted_index = self._build_inverted_index()
        
        # Calculate average document length (used for normalization)
        self.avg_doc_length = self._calculate_avg_doc_length()
        
        # Calculate IDF (Inverse Document Frequency) for each word
        self.idf_scores = self._calculate_idf()
        
        print(f"✅ BM25 initialized with {len(documents)} documents")
    
    
    def _tokenize(self, text):
        """
        Split text into words (tokens)
        
        Simple approach: split by whitespace and convert to lowercase
        
        Args:
            text: String to tokenize
            
        Returns:
            List of words
        """
        if not text:
            return []
        
        # Convert to lowercase and split by spaces
        # Remove punctuation and keep only alphanumeric characters
        words = text.lower().split()
        
        return words
    
    
    def _build_inverted_index(self):
        """
        Build inverted index: {word: {doc_id: frequency}}
        
        Example:
        {
            'আমির': {0: 2, 5: 1},  # 'আমির' appears 2 times in doc 0, 1 time in doc 5
            'খান': {0: 2, 5: 1, 10: 1}
        }
        
        Returns:
            Dictionary mapping words to document IDs and their frequencies
        """
        inverted_index = defaultdict(lambda: defaultdict(int))
        
        # Go through each document
        for doc_id, doc in enumerate(self.documents):
            # Combine title and body for searching
            text = (doc.get('title', '') + ' ' + doc.get('body', '')).strip()
            
            # Split into words
            words = self._tokenize(text)
            
            # Count how many times each word appears in this document
            word_counts = Counter(words)
            
            # Store in inverted index
            for word, count in word_counts.items():
                inverted_index[word][doc_id] = count
        
        return inverted_index
    
    
    def _calculate_avg_doc_length(self):
        """
        Calculate the average length of all documents
        This is used to normalize scores (so short docs aren't unfairly favored)
        
        Returns:
            Average document length in number of words
        """
        total_length = 0
        
        for doc in self.documents:
            text = (doc.get('title', '') + ' ' + doc.get('body', '')).strip()
            words = self._tokenize(text)
            total_length += len(words)
        
        avg_length = total_length / len(self.documents) if self.documents else 0
        return avg_length
    
    
    def _calculate_idf(self):
        """
        Calculate IDF (Inverse Document Frequency) for each word
        
        IDF tells us how "important" or "rare" a word is:
        - Common words (like "the", "a") get LOW IDF score
        - Rare words (like "আমির", "ক্রিকেট") get HIGH IDF score
        
        Formula: IDF(word) = log((N - df + 0.5) / (df + 0.5))
        where N = total documents, df = documents containing the word
        
        Returns:
            Dictionary mapping words to their IDF scores
        """
        idf_scores = {}
        N = len(self.documents)  # Total number of documents
        
        for word, doc_dict in self.inverted_index.items():
            df = len(doc_dict)  # How many documents contain this word
            
            # Calculate IDF using BM25 formula
            idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
            idf_scores[word] = idf
        
        return idf_scores
    
    
    def _calculate_bm25_score(self, query_words, doc_id):
        """
        Calculate BM25 score for a single document
        
        The score considers:
        1. How many query words appear in the document
        2. How often they appear (term frequency)
        3. How rare/important each word is (IDF)
        4. Document length normalization
        
        Args:
            query_words: List of words in the query
            doc_id: ID of the document to score
            
        Returns:
            BM25 score (higher = more relevant)
        """
        score = 0.0
        
        # Get document text and length
        doc = self.documents[doc_id]
        text = (doc.get('title', '') + ' ' + doc.get('body', '')).strip()
        doc_length = len(self._tokenize(text))
        
        # For each word in the query
        for word in query_words:
            word = word.lower()
            
            # Skip if word not in any document
            if word not in self.inverted_index:
                continue
            
            # Skip if word not in this specific document
            if doc_id not in self.inverted_index[word]:
                continue
            
            # Get term frequency (how many times word appears in this doc)
            tf = self.inverted_index[word][doc_id]
            
            # Get IDF (how rare/important this word is)
            idf = self.idf_scores.get(word, 0)
            
            # Calculate BM25 component for this word
            # Numerator: TF weighted by (k1 + 1)
            numerator = tf * (self.k1 + 1)
            
            # Denominator: Adds saturation and length normalization
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
            
            # Add to total score
            score += idf * (numerator / denominator)
        
        return score
    
    
    def search(self, query, k=10):
        """
        Search for documents matching the query
        
        Args:
            query: Search query string (e.g., "আমির খান")
            k: Number of top results to return (default: 10)
            
        Returns:
            List of tuples: [(doc_id, score, document), ...]
            Sorted by score (highest first)
        """
        # Split query into words
        query_words = self._tokenize(query)
        
        if not query_words:
            return []
        
        # Find all candidate documents (documents containing at least one query word)
        candidate_docs = set()
        for word in query_words:
            word = word.lower()
            if word in self.inverted_index:
                candidate_docs.update(self.inverted_index[word].keys())
        
        # Score each candidate document
        results = []
        for doc_id in candidate_docs:
            score = self._calculate_bm25_score(query_words, doc_id)
            results.append((doc_id, score, self.documents[doc_id]))
        
        # Sort by score (highest first) and return top k
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:k]


# Example usage (for testing)
if __name__ == "__main__":
    # Sample test
    sample_docs = [
        {"title": "আমির খান", "body": "হিন্দি সিনেমার দুনিয়ায় আমির খান পরিচিত"},
        {"title": "Cricket", "body": "Bangladesh cricket team won the match"},
        {"title": "ঢাকা", "body": "ঢাকা বাংলাদেশের রাজধানী"}
    ]
    
    # Initialize BM25
    bm25 = BM25Search(sample_docs)
    
    # Search
    results = bm25.search("আমির খান", k=5)
    
    # Print results
    print("\n🔍 Search Results:")
    for doc_id, score, doc in results:
        print(f"  Score: {score:.2f} - {doc['title']}")
