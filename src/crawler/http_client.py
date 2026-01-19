"""
HTTP client with rate limiting, retries, and robust error handling.
"""

import time
import random
import logging
from typing import Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import (
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    MAX_RETRIES,
    RETRY_BACKOFF,
    USER_AGENTS,
)

logger = logging.getLogger(__name__)


class HttpClient:
    """
    Robust HTTP client for web crawling.
    
    Features:
    - Rate limiting between requests
    - Automatic retries with exponential backoff
    - Rotating user agents
    - Connection pooling
    - UTF-8 encoding enforcement
    """
    
    def __init__(
        self,
        delay: float = REQUEST_DELAY,
        timeout: int = REQUEST_TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ):
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.last_request_time = 0.0
        
        # Create session with retry strategy
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a session with retry configuration."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _get_headers(self, language: str = "en") -> dict:
        """Get request headers with random user agent."""
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        
        # Set Accept-Language based on target
        if language == "bn":
            headers["Accept-Language"] = "bn-BD,bn;q=0.9,en-US;q=0.8,en;q=0.7"
        else:
            headers["Accept-Language"] = "en-US,en;q=0.9"
        
        return headers
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            sleep_time = self.delay - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
    
    def get(
        self,
        url: str,
        language: str = "en",
        base_url: Optional[str] = None,
    ) -> Optional[str]:
        """
        Fetch a URL and return the HTML content.
        
        Args:
            url: URL to fetch (can be relative if base_url provided)
            language: 'en' or 'bn' for Accept-Language header
            base_url: Base URL for resolving relative URLs
        
        Returns:
            HTML content as string, or None if request failed
        """
        # Resolve relative URLs
        if base_url and not url.startswith("http"):
            url = urljoin(base_url, url)
        
        # Apply rate limiting
        self._rate_limit()
        
        try:
            logger.debug(f"Fetching: {url}")
            
            response = self.session.get(
                url,
                headers=self._get_headers(language),
                timeout=self.timeout,
            )
            
            self.last_request_time = time.time()
            
            # Check for success
            response.raise_for_status()
            
            # Force UTF-8 encoding for Bangla content
            if language == "bn":
                response.encoding = "utf-8"
            elif response.encoding is None:
                response.encoding = response.apparent_encoding
            
            return response.text
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
            return None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limited by server, backing off: {url}")
                time.sleep(60)  # Back off for 60 seconds
                return self.get(url, language, base_url)  # Retry once
            logger.warning(f"HTTP error {e.response.status_code} for {url}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def close(self):
        """Close the session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
