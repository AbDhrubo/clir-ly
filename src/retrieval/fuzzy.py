"""
Module C - Fuzzy Search Implementation
======================================
This file implements fuzzy matching for handling typos and transliteration.

What does Fuzzy Search do?
- It finds documents even when there are spelling mistakes
- It handles transliteration (e.g., "Dhaka" ↔ "ঢাকা" written as "Dhaka")
- It matches similar-sounding or similar-looking words

Simple Example:
Query: "Shakib" (user made a typo)
- Fuzzy search will still find "Sakib" 
- It calculates similarity percentage (0-100)
- Words with >70% similarity are considered matches

Methods Used:
1. Levenshtein Distance: Counts how many edits needed to change one word to another
2. Character N-grams: Breaks words into chunks and compares chunks
"""

from fuzzywuzzy import fuzz
from collections import defaultdict


class FuzzySearch:
    """
    Fuzzy Search for handling typos and transliteration
    
    Parameters:
    - threshold: Minimum similarity score (0-100) to consider a match
                 Default: 70 (means 70% similar)
    """
    
    def __init__(self, documents, threshold=70):
        """
        Initialize Fuzzy Search with documents
        
        Args:
            documents: List of dictionaries with 'body' and 'title' fields
            threshold: Minimum similarity percentage for a match (default: 70)
        """
        self.documents = documents
        self.threshold = threshold
        
        # Build word index: all unique words and their document locations
        self.word_index = self._build_word_index()
        
        print(f"✅ Fuzzy Search initialized with {len(documents)} documents")
        print(f"   Threshold: {threshold}% similarity")
    
    
    def _tokenize(self, text):
        """
        Split text into words
        
        Args:
            text: String to split
            
        Returns:
            List of words (lowercase)
        """
        if not text:
            return []
        
        # Simple tokenization: split by spaces, convert to lowercase
        words = text.lower().split()
        return words
    
    
    def _build_word_index(self):
        """
        Build index of all words in all documents
        This helps us quickly find which documents contain which words
        
        Returns:
            Dictionary: {word: [doc_id1, doc_id2, ...]}
        """
        word_index = defaultdict(set)
        
        for doc_id, doc in enumerate(self.documents):
            # Combine title and body
            text = (doc.get('title', '') + ' ' + doc.get('body', '')).strip()
            
            # Get all words
            words = self._tokenize(text)
            
            # Add to index
            for word in words:
                word_index[word].add(doc_id)
        
        return word_index
    
    
    def _fuzzy_match_word(self, query_word, doc_word):
        """
        Calculate similarity between two words using fuzzy matching
        
        Uses Levenshtein distance to measure similarity:
        - 100 = exactly same
        - 90+ = very similar (1-2 character difference)
        - 70-89 = somewhat similar
        - <70 = different words
        
        Args:
            query_word: Word from user's query
            doc_word: Word from document
            
        Returns:
            Similarity score (0-100)
        """
        # Calculate similarity using fuzz ratio
        similarity = fuzz.ratio(query_word.lower(), doc_word.lower())
        
        return similarity
    
    
    def _char_ngrams(self, word, n=3):
        """
        Break word into character n-grams (chunks)
        
        This helps match words that sound similar or are transliterated
        
        Example:
        word = "Bangladesh", n = 3
        Returns: ['ban', 'ang', 'ngl', 'gla', 'lad', 'ade', 'des', 'esh']
        
        Args:
            word: Word to break into n-grams
            n: Size of each chunk (default: 3)
            
        Returns:
            List of character n-grams
        """
        word = word.lower()
        
        # If word is too short, return the word itself
        if len(word) < n:
            return [word]
        
        # Generate n-grams
        ngrams = []
        for i in range(len(word) - n + 1):
            ngrams.append(word[i:i+n])
        
        return ngrams
    
    
    def _ngram_similarity(self, word1, word2, n=3):
        """
        Calculate similarity based on common n-grams
        
        Useful for transliteration matching:
        - "Dhaka" vs "dhaka" vs "Dhakar"
        - "Bangladesh" vs "banglades"
        
        Args:
            word1: First word
            word2: Second word
            n: N-gram size (default: 3)
            
        Returns:
            Similarity score (0-100)
        """
        # Get n-grams for both words
        ngrams1 = set(self._char_ngrams(word1, n))
        ngrams2 = set(self._char_ngrams(word2, n))
        
        # If either set is empty, return 0
        if not ngrams1 or not ngrams2:
            return 0
        
        # Calculate Jaccard similarity: intersection / union
        intersection = len(ngrams1 & ngrams2)
        union = len(ngrams1 | ngrams2)
        
        similarity = (intersection / union) * 100 if union > 0 else 0
        
        return similarity
    
    
    def _find_fuzzy_matches(self, query_word):
        """
        Find all words in documents that fuzzily match the query word
        
        Args:
            query_word: Word to match
            
        Returns:
            List of tuples: [(doc_word, similarity_score, doc_ids), ...]
        """
        matches = []
        
        # Check each word in our word index
        for doc_word, doc_ids in self.word_index.items():
            # Calculate fuzzy similarity
            fuzzy_sim = self._fuzzy_match_word(query_word, doc_word)
            
            # Also calculate n-gram similarity
            ngram_sim = self._ngram_similarity(query_word, doc_word)
            
            # Take the maximum of both similarities
            max_similarity = max(fuzzy_sim, ngram_sim)
            
            # If similarity is above threshold, it's a match
            if max_similarity >= self.threshold:
                matches.append((doc_word, max_similarity, doc_ids))
        
        return matches
    
    
    def search(self, query, k=10):
        """
        Search for documents using fuzzy matching
        
        This is useful when:
        - User makes typos
        - User uses transliteration (English letters for Bangla words)
        - Word variations (plural, tense changes)
        
        Args:
            query: Search query string
            k: Number of top results to return
            
        Returns:
            List of tuples: [(doc_id, score, document), ...]
        """
        # Split query into words
        query_words = self._tokenize(query)
        
        if not query_words:
            return []
        
        # Store document scores
        doc_scores = defaultdict(float)
        
        # For each word in the query
        for query_word in query_words:
            # Find fuzzy matches in documents
            matches = self._find_fuzzy_matches(query_word)
            
            # For each match, add score to relevant documents
            for doc_word, similarity, doc_ids in matches:
                for doc_id in doc_ids:
                    # Add normalized similarity score (0-1 range)
                    doc_scores[doc_id] += similarity / 100.0
        
        # Convert to list and sort by score
        results = []
        for doc_id, score in doc_scores.items():
            results.append((doc_id, score, self.documents[doc_id]))
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        return results[:k]


# Example usage (for testing)
if __name__ == "__main__":
    # Sample test
    sample_docs = [
        {"title": "Shakib Al Hasan", "body": "Shakib is a great cricketer from Bangladesh"},
        {"title": "Dhaka City", "body": "Dhaka is the capital of Bangladesh"},
        {"title": "আমির খান", "body": "আমির খান বলিউডের অভিনেতা"}
    ]
    
    # Initialize Fuzzy Search
    fuzzy = FuzzySearch(sample_docs, threshold=70)
    
    # Test 1: Typo in name
    print("\n🔍 Search: 'Sakib' (typo for Shakib)")
    results = fuzzy.search("Sakib", k=5)
    for doc_id, score, doc in results:
        print(f"  Score: {score:.2f} - {doc['title']}")
    
    # Test 2: Partial word
    print("\n🔍 Search: 'Dhakar' (partial/typo)")
    results = fuzzy.search("Dhakar", k=5)
    for doc_id, score, doc in results:
        print(f"  Score: {score:.2f} - {doc['title']}")
