"""
Module C - Semantic Search Implementation
=========================================
This file implements semantic search using multilingual embeddings.

What does Semantic Search do?
- It understands the MEANING of words, not just exact matches
- It works across languages (English query can find Bangla documents)
- It finds documents with similar concepts, even if words are different

Simple Example:
Query: "cricket player" (English)
- Can find: "ক্রিকেট খেলোয়াড়" (Bangla)
- Can find: "batsman", "bowler" (related concepts)
- Works because it understands meaning, not just words

How it works:
1. Convert documents into "embeddings" (arrays of numbers representing meaning)
2. Convert query into embedding
3. Find documents with embeddings most similar to query embedding
4. Use cosine similarity to measure closeness

Model Used: LaBSE (Language-agnostic BERT Sentence Embedding)
- Supports 100+ languages including English and Bangla
- Pre-trained to align similar meanings across languages
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os


class SemanticSearch:
    """
    Semantic Search using multilingual embeddings
    
    This allows cross-lingual search:
    - English query → Find Bangla documents
    - Bangla query → Find English documents
    - Understands synonyms and related concepts
    """
    
    def __init__(self, documents, model_name='sentence-transformers/LaBSE'):
        """
        Initialize Semantic Search
        
        Args:
            documents: List of dictionaries with 'body' and 'title' fields
            model_name: Name of the embedding model to use
                       Default: LaBSE (best for Bangla-English)
        """
        self.documents = documents
        self.model_name = model_name
        
        print(f"📥 Loading embedding model: {model_name}")
        print("   (This may take a minute on first run...)")
        
        # Load the pre-trained model
        # This model converts text to 768-dimensional vectors
        self.model = SentenceTransformer(model_name)
        
        print(f"✅ Model loaded successfully!")
        
        # Pre-compute embeddings for all documents
        # We do this once and save, so we don't have to recompute every time
        self.doc_embeddings = self._compute_document_embeddings()
        
        print(f"✅ Semantic Search initialized with {len(documents)} documents")
    
    
    def _compute_document_embeddings(self):
        """
        Convert all documents into embeddings (vector representations)
        
        Each document becomes a 768-dimensional vector that represents its meaning.
        Similar documents will have similar vectors.
        
        Returns:
            numpy array of shape (num_documents, 768)
        """
        # Check if we have pre-computed embeddings saved
        embeddings_file = 'document_embeddings.pkl'
        
        if os.path.exists(embeddings_file):
            print(f"📂 Loading pre-computed embeddings from {embeddings_file}")
            with open(embeddings_file, 'rb') as f:
                return pickle.load(f)
        
        print("🔄 Computing embeddings for all documents...")
        print("   (This will take some time but only happens once)")
        
        # Prepare all document texts
        doc_texts = []
        for doc in self.documents:
            # Combine title and body
            # Title often contains important keywords, so we give it extra weight
            text = doc.get('title', '') + '. ' + doc.get('body', '')
            doc_texts.append(text.strip())
        
        # Encode all documents at once (batch processing is faster)
        # This converts each text into a 768-dimensional vector
        embeddings = self.model.encode(
            doc_texts,
            show_progress_bar=True,  # Show progress as it processes
            batch_size=32,           # Process 32 documents at a time
            convert_to_numpy=True    # Return as numpy array
        )
        
        # Save embeddings for future use
        print(f"💾 Saving embeddings to {embeddings_file}")
        with open(embeddings_file, 'wb') as f:
            pickle.dump(embeddings, f)
        
        return embeddings
    
    
    def search(self, query, k=10):
        """
        Search for semantically similar documents
        
        Process:
        1. Convert query to embedding (vector)
        2. Calculate cosine similarity with all document embeddings
        3. Return top k most similar documents
        
        Cosine Similarity:
        - Measures angle between two vectors
        - 1.0 = exactly same meaning
        - 0.0 = completely unrelated
        - Works great for semantic similarity
        
        Args:
            query: Search query string (can be English or Bangla)
            k: Number of top results to return
            
        Returns:
            List of tuples: [(doc_id, similarity_score, document), ...]
            Sorted by similarity (highest first)
        """
        if not query.strip():
            return []
        
        print(f"\n🔍 Searching for: '{query}'")
        
        # Convert query to embedding
        # This creates a 768-dimensional vector representing the query's meaning
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True
        )
        
        # Calculate cosine similarity between query and all documents
        # Result: array of similarity scores, one for each document
        similarities = cosine_similarity(
            query_embedding,
            self.doc_embeddings
        )[0]  # [0] because query_embedding is 2D array [[...]]
        
        # Create list of (doc_id, score, document)
        results = []
        for doc_id, similarity in enumerate(similarities):
            results.append((doc_id, float(similarity), self.documents[doc_id]))
        
        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Return top k results
        return results[:k]
    
    
    def save_embeddings(self, filepath='document_embeddings.pkl'):
        """
        Save computed embeddings to file
        This way you don't have to recompute them every time
        
        Args:
            filepath: Where to save the embeddings
        """
        with open(filepath, 'wb') as f:
            pickle.dump(self.doc_embeddings, f)
        print(f"💾 Embeddings saved to {filepath}")
    
    
    def load_embeddings(self, filepath='document_embeddings.pkl'):
        """
        Load pre-computed embeddings from file
        
        Args:
            filepath: Where to load the embeddings from
        """
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.doc_embeddings = pickle.load(f)
            print(f"📂 Embeddings loaded from {filepath}")
            return True
        else:
            print(f"❌ File {filepath} not found")
            return False


# Example usage (for testing)
if __name__ == "__main__":
    # Sample test documents
    sample_docs = [
        {
            "title": "আমির খান",
            "body": "হিন্দি সিনেমার দুনিয়ায় আমির খান 'মিস্টার পারফেকশনিস্ট' হিসেবে পরিচিত"
        },
        {
            "title": "Cricket News",
            "body": "Bangladesh cricket team won the match against strong opponents"
        },
        {
            "title": "ঢাকা শহর",
            "body": "ঢাকা বাংলাদেশের রাজধানী এবং বৃহত্তম শহর"
        }
    ]
    
    print("=" * 60)
    print("Testing Semantic Search")
    print("=" * 60)
    
    # Initialize Semantic Search
    semantic = SemanticSearch(sample_docs)
    
    # Test 1: English query for Bangla document
    print("\n" + "=" * 60)
    print("Test 1: Cross-lingual search (English → Bangla)")
    print("=" * 60)
    results = semantic.search("Aamir Khan perfectionist", k=3)
    for doc_id, score, doc in results:
        print(f"  Score: {score:.3f} - {doc['title']}")
    
    # Test 2: Bangla query for English document
    print("\n" + "=" * 60)
    print("Test 2: Cross-lingual search (Bangla → English)")
    print("=" * 60)
    results = semantic.search("ক্রিকেট খেলা", k=3)
    for doc_id, score, doc in results:
        print(f"  Score: {score:.3f} - {doc['title']}")
    
    # Test 3: Semantic similarity
    print("\n" + "=" * 60)
    print("Test 3: Semantic similarity (capital city → Dhaka)")
    print("=" * 60)
    results = semantic.search("capital city Bangladesh", k=3)
    for doc_id, score, doc in results:
        print(f"  Score: {score:.3f} - {doc['title']}")
