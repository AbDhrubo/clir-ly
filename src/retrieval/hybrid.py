"""
Module C - Hybrid Search Implementation
=======================================
This file combines BM25, Fuzzy, and Semantic search into one powerful search system.

What does Hybrid Search do?
- Takes the best from all three methods:
  * BM25: Good at exact keyword matching
  * Fuzzy: Handles typos and transliteration
  * Semantic: Understands meaning and works cross-lingually
- Combines their scores intelligently
- Gives you the most relevant results overall

Simple Example:
Query: "Amir Khan actor" (with typo)
- BM25: Might miss due to typo
- Fuzzy: Finds "আমির খান" despite spelling difference
- Semantic: Understands "actor" relates to the article about movies
- Hybrid: Combines all signals to rank best result first

How it works:
1. Run all three search methods
2. Normalize scores to 0-1 range (they use different scales)
3. Combine with weighted average
4. Return top results
"""

import time
from .bm25 import BM25Search
from .fuzzy import FuzzySearch
from .semantic import SemanticSearch


class HybridSearch:
    """
    Hybrid Search: Combines BM25, Fuzzy, and Semantic search
    
    Parameters (weights for combining scores):
    - alpha: Weight for BM25 (keyword matching)
    - beta: Weight for Semantic (meaning understanding)
    - gamma: Weight for Fuzzy (typo/transliteration handling)
    
    Default: (0.2, 0.6, 0.2)
    - We favor semantic search because it handles cross-lingual well
    - BM25 and Fuzzy provide additional signal
    """
    
    def __init__(self, documents, alpha=0.2, beta=0.6, gamma=0.2):
        """
        Initialize Hybrid Search with all three methods
        
        Args:
            documents: List of dictionaries with 'body' and 'title' fields
            alpha: Weight for BM25 scores (default: 0.2)
            beta: Weight for Semantic scores (default: 0.6)
            gamma: Weight for Fuzzy scores (default: 0.2)
        """
        self.documents = documents
        self.alpha = alpha    # BM25 weight
        self.beta = beta      # Semantic weight
        self.gamma = gamma    # Fuzzy weight
        
        # Ensure weights sum to 1.0
        total = alpha + beta + gamma
        if abs(total - 1.0) > 0.001:  # Allow small floating point errors
            print(f"⚠️  Warning: Weights sum to {total}, normalizing to 1.0")
            self.alpha = alpha / total
            self.beta = beta / total
            self.gamma = gamma / total
        
        print(f"\n{'='*60}")
        print(f"Initializing Hybrid Search")
        print(f"{'='*60}")
        print(f"Weights: BM25={self.alpha:.1%}, Semantic={self.beta:.1%}, Fuzzy={self.gamma:.1%}")
        print()
        
        # Initialize all three search methods
        print("1️⃣  Initializing BM25 Search...")
        self.bm25 = BM25Search(documents)
        
        print("\n2️⃣  Initializing Fuzzy Search...")
        self.fuzzy = FuzzySearch(documents, threshold=70)
        
        print("\n3️⃣  Initializing Semantic Search...")
        self.semantic = SemanticSearch(documents)
        
        print(f"\n{'='*60}")
        print(f"✅ Hybrid Search Ready!")
        print(f"{'='*60}\n")
    
    
    def _normalize_scores(self, results):
        """
        Normalize scores to 0-1 range using min-max normalization
        
        Why normalize?
        - BM25 scores: typically 0-20+
        - Fuzzy scores: 0-100 (but we divide by 100, so 0-1)
        - Semantic scores: 0-1
        
        We need them all in the same range to combine fairly!
        
        Formula: normalized = (score - min) / (max - min)
        
        Args:
            results: List of tuples [(doc_id, score, document), ...]
            
        Returns:
            Dictionary: {doc_id: normalized_score}
        """
        if not results:
            return {}
        
        # Extract scores
        scores = [score for _, score, _ in results]
        
        # Find min and max
        min_score = min(scores)
        max_score = max(scores)
        
        # Avoid division by zero
        if max_score == min_score:
            # All scores are the same, return 1.0 for all
            return {doc_id: 1.0 for doc_id, _, _ in results}
        
        # Normalize each score
        normalized = {}
        for doc_id, score, _ in results:
            normalized[doc_id] = (score - min_score) / (max_score - min_score)
        
        return normalized
    
    
    def search(self, query, k=10, verbose=False, confidence_threshold=0.20, return_timing=False):
        """
        Search using hybrid approach (combines all three methods)
        
        Process:
        1. Get results from BM25, Fuzzy, and Semantic search
        2. Normalize all scores to 0-1 range
        3. Combine scores using weighted average
        4. Sort by combined score and return top k
        5. Check confidence and display warning if needed
        
        Args:
            query: Search query string
            k: Number of top results to return
            verbose: If True, print detailed scoring information
            confidence_threshold: Minimum score threshold for confidence warning (default: 0.20)
            return_timing: If True, return timing breakdown in results
            
        Returns:
            List of tuples: [(doc_id, combined_score, document, score_breakdown), ...]
            score_breakdown = {'bm25': x, 'fuzzy': y, 'semantic': z}
            If return_timing=True, also returns timing dict as second element
        """
        # Track total time
        start_time = time.time()
        timing = {}
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"🔍 Hybrid Search Query: '{query}'")
            print(f"{'='*60}\n")
        
        # 1. Get results from each method (with timing)
        if verbose:
            print("Running BM25 search...")
        bm25_start = time.time()
        bm25_results = self.bm25.search(query, k=len(self.documents))
        timing['bm25_ms'] = (time.time() - bm25_start) * 1000
        
        if verbose:
            print("Running Fuzzy search...")
        fuzzy_start = time.time()
        fuzzy_results = self.fuzzy.search(query, k=len(self.documents))
        timing['fuzzy_ms'] = (time.time() - fuzzy_start) * 1000
        
        if verbose:
            print("Running Semantic search...")
        semantic_start = time.time()
        semantic_results = self.semantic.search(query, k=len(self.documents))
        timing['semantic_ms'] = (time.time() - semantic_start) * 1000
        
        # 2. Normalize scores from BM25 and Fuzzy
        if verbose:
            print("Combining results...")
        ranking_start = time.time()
        bm25_scores = self._normalize_scores(bm25_results)
        fuzzy_scores = self._normalize_scores(fuzzy_results)
        
        # For semantic: DON'T normalize - use raw cosine similarity (already 0-1)
        # This prevents inflating poor matches when all results are bad
        semantic_scores = {doc_id: score for doc_id, score, _ in semantic_results}
        
        # 3. Combine scores
        # Get all unique document IDs that appeared in any result
        all_doc_ids = set()
        all_doc_ids.update(bm25_scores.keys())
        all_doc_ids.update(fuzzy_scores.keys())
        all_doc_ids.update(semantic_scores.keys())
        
        # Calculate combined score for each document
        combined_results = []
        
        for doc_id in all_doc_ids:
            # Get normalized scores (default to 0 if document not in that method's results)
            bm25_score = bm25_scores.get(doc_id, 0.0)
            fuzzy_score = fuzzy_scores.get(doc_id, 0.0)
            semantic_score = semantic_scores.get(doc_id, 0.0)
            
            # Calculate weighted combination
            combined_score = (
                self.alpha * bm25_score +
                self.beta * semantic_score +
                self.gamma * fuzzy_score
            )
            
            # Store result with breakdown
            score_breakdown = {
                'bm25': bm25_score,
                'fuzzy': fuzzy_score,
                'semantic': semantic_score
            }
            
            combined_results.append((
                doc_id,
                combined_score,
                self.documents[doc_id],
                score_breakdown
            ))
        
        # 4. Sort by combined score (highest first)
        combined_results.sort(key=lambda x: x[1], reverse=True)
        timing['ranking_ms'] = (time.time() - ranking_start) * 1000
        
        # 5. Return top k results
        top_results = combined_results[:k]
        
        # 6. Check confidence and display warning if needed
        if top_results:
            top_score = top_results[0][1]  # Get the score of the top result
            if top_score < confidence_threshold:
                print(f"\n{'⚠️ '*20}")
                print(f"⚠️  WARNING: Retrieved results may not be relevant.")
                print(f"⚠️  Matching confidence is low (score: {top_score:.2f}).")
                print(f"⚠️  Consider rephrasing your query or checking translation quality.")
                print(f"{'⚠️ '*20}\n")
        
        # Print verbose output if requested
        if verbose:
            print(f"\n{'='*60}")
            print(f"Top {k} Results:")
            print(f"{'='*60}\n")
            
            for i, (doc_id, score, doc, breakdown) in enumerate(top_results, 1):
                print(f"{i}. Score: {score:.3f}")
                print(f"   Title: {doc.get('title', 'N/A')}")
                print(f"   Breakdown:")
                print(f"     • BM25:     {breakdown['bm25']:.3f} (×{self.alpha:.1%} = {breakdown['bm25']*self.alpha:.3f})")
                print(f"     • Fuzzy:    {breakdown['fuzzy']:.3f} (×{self.gamma:.1%} = {breakdown['fuzzy']*self.gamma:.3f})")
                print(f"     • Semantic: {breakdown['semantic']:.3f} (×{self.beta:.1%} = {breakdown['semantic']*self.beta:.3f})")
                print()
        
        # Calculate total time
        timing['total_ms'] = (time.time() - start_time) * 1000
        
        # Print timing if verbose
        if verbose and return_timing:
            print(f"\n{'='*60}")
            print(f"⏱️  Execution Time Breakdown:")
            print(f"{'='*60}")
            print(f"  BM25 Search:     {timing['bm25_ms']:>8.2f} ms")
            print(f"  Fuzzy Search:    {timing['fuzzy_ms']:>8.2f} ms")
            print(f"  Semantic Search: {timing['semantic_ms']:>8.2f} ms")
            print(f"  Ranking/Combine: {timing['ranking_ms']:>8.2f} ms")
            print(f"  {'─'*60}")
            print(f"  Total Time:      {timing['total_ms']:>8.2f} ms")
            print(f"{'='*60}\n")
        
        # Return results with or without timing
        if return_timing:
            return top_results, timing
        else:
            return top_results
    
    
    def search_with_method(self, query, method='hybrid', k=10, confidence_threshold=0.20, return_timing=False):
        """
        Search using a specific method or hybrid
        
        Useful for comparing different approaches
        
        Args:
            query: Search query
            method: 'bm25', 'fuzzy', 'semantic', or 'hybrid'
            k: Number of results
            confidence_threshold: Minimum score threshold for confidence warning (only for hybrid)
            return_timing: If True, return timing information
            
        Returns:
            Search results from the specified method
        """
        if method == 'bm25':
            return self.bm25.search(query, k)
        elif method == 'fuzzy':
            return self.fuzzy.search(query, k)
        elif method == 'semantic':
            return self.semantic.search(query, k)
        elif method == 'hybrid':
            return self.search(query, k, confidence_threshold=confidence_threshold, return_timing=return_timing)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'bm25', 'fuzzy', 'semantic', or 'hybrid'")


# Example usage (for testing)
if __name__ == "__main__":
    # Sample test documents
    sample_docs = [
        {
            "title": "আমির খান",
            "body": "হিন্দি সিনেমার দুনিয়ায় আমির খান 'মিস্টার পারফেকশনিস্ট' হিসেবে পরিচিত"
        },
        {
            "title": "Cricket Match",
            "body": "Bangladesh cricket team won the match with excellent batting"
        },
        {
            "title": "ঢাকা শহর",
            "body": "ঢাকা বাংলাদেশের রাজধানী এবং বৃহত্তম শহর"
        }
    ]
    
    # Initialize Hybrid Search
    hybrid = HybridSearch(sample_docs)
    
    # Test search with verbose output
    print("\n" + "="*60)
    print("Test: Cross-lingual search with typo")
    print("="*60)
    
    results = hybrid.search("Amir Khan actor", k=3, verbose=True)
