"""
Tavily API client for extracting content from heavily protected sites.

Tavily provides AI-powered web scraping that bypasses Cloudflare and other
bot protection mechanisms by rendering pages server-side.
"""

import os
import logging
from typing import Optional, List, Dict
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file from project root
_env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(_env_path)


class TavilyClient:
    """
    Client for Tavily API content extraction.
    
    Uses Tavily's extract endpoint to get clean content from URLs
    that are protected by Cloudflare or other anti-bot measures.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Tavily client.
        
        Args:
            api_key: Tavily API key. If not provided, reads from TAVILY_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found. Set it in .env file or pass directly.")
            self._client = None
        else:
            try:
                from tavily import TavilyClient as _TavilyClient
                self._client = _TavilyClient(api_key=self.api_key)
                logger.info("TavilyClient initialized successfully")
            except ImportError:
                logger.error("tavily-python not installed. Run: pip install tavily-python")
                self._client = None
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {e}")
                self._client = None
    
    @property
    def is_available(self) -> bool:
        """Check if the Tavily client is available."""
        return self._client is not None
    
    def extract(self, url: str) -> Optional[Dict]:
        """
        Extract content from a URL using Tavily.
        
        Args:
            url: URL to extract content from
            
        Returns:
            Dict with 'title', 'content', 'url' or None if extraction failed
        """
        if not self._client:
            logger.error("Tavily client not initialized")
            return None
        
        try:
            logger.debug(f"Tavily extracting: {url}")
            result = self._client.extract(urls=[url])
            
            if result and "results" in result and len(result["results"]) > 0:
                extracted = result["results"][0]
                return {
                    "url": extracted.get("url", url),
                    "title": self._extract_title(extracted),
                    "content": extracted.get("raw_content", ""),
                }
            
            logger.warning(f"No content extracted from: {url}")
            return None
            
        except Exception as e:
            logger.error(f"Tavily extraction failed for {url}: {e}")
            return None
    
    def extract_batch(self, urls: List[str]) -> List[Optional[Dict]]:
        """
        Extract content from multiple URLs in a single API call.
        
        Args:
            urls: List of URLs to extract content from
            
        Returns:
            List of extraction results (None for failed extractions)
        """
        if not self._client:
            logger.error("Tavily client not initialized")
            return [None] * len(urls)
        
        try:
            logger.debug(f"Tavily batch extracting {len(urls)} URLs")
            result = self._client.extract(urls=urls)
            
            results = []
            if result and "results" in result:
                # Create a map of URL to result
                url_map = {r.get("url"): r for r in result["results"]}
                
                for url in urls:
                    if url in url_map:
                        extracted = url_map[url]
                        results.append({
                            "url": url,
                            "title": self._extract_title(extracted),
                            "content": extracted.get("raw_content", ""),
                        })
                    else:
                        results.append(None)
            else:
                results = [None] * len(urls)
            
            return results
            
        except Exception as e:
            logger.error(f"Tavily batch extraction failed: {e}")
            return [None] * len(urls)
    
    def _extract_title(self, extracted: Dict) -> str:
        """Extract title from Tavily response."""
        # Try different fields that might contain the title
        if "title" in extracted:
            return extracted["title"]
        
        # Try to extract from raw_content first line
        content = extracted.get("raw_content", "")
        if content:
            first_line = content.split("\n")[0].strip()
            if len(first_line) < 200:  # Reasonable title length
                return first_line
        
        return ""


# Singleton instance
_tavily_client: Optional[TavilyClient] = None


def get_tavily_client() -> TavilyClient:
    """Get or create a singleton Tavily client."""
    global _tavily_client
    if _tavily_client is None:
        _tavily_client = TavilyClient()
    return _tavily_client


def is_tavily_available() -> bool:
    """Check if Tavily API is available."""
    return get_tavily_client().is_available
