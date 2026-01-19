"""
Cloudscraper-based HTTP client for Cloudflare-protected sites.

cloudscraper automatically solves Cloudflare's anti-bot challenges
without requiring a browser.
"""

import logging
import time
from typing import Optional, Dict
from urllib.parse import urljoin

import cloudscraper

logger = logging.getLogger(__name__)


class CloudscraperClient:
    """
    HTTP client using cloudscraper to bypass Cloudflare protection.
    
    This is more lightweight than Selenium and can handle most
    Cloudflare challenges automatically.
    """
    
    def __init__(
        self,
        delay: float = 2.0,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the cloudscraper client.
        
        Args:
            delay: Delay between requests in seconds
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries per request
        """
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request_time = 0
        
        # Create cloudscraper session with browser impersonation
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False,
            },
            delay=10,  # Delay for solving challenges
        )
        
        logger.info("CloudscraperClient initialized")
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
    
    def get(
        self,
        url: str,
        language: str = "en",
        headers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Fetch a URL with Cloudflare bypass.
        
        Args:
            url: URL to fetch
            language: 'en' or 'bn' for Accept-Language header
            headers: Additional headers to include
            
        Returns:
            HTML content as string, or None if request failed
        """
        self._rate_limit()
        
        request_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "bn-BD,bn;q=0.9,en;q=0.8" if language == "bn" else "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
        
        if headers:
            request_headers.update(headers)
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Cloudscraper fetching: {url} (attempt {attempt + 1})")
                
                response = self.scraper.get(
                    url,
                    headers=request_headers,
                    timeout=self.timeout,
                )
                
                self._last_request_time = time.time()
                
                # Check for success
                if response.status_code == 200:
                    # Force UTF-8 for Bangla content
                    if language == "bn":
                        response.encoding = "utf-8"
                    elif response.encoding is None:
                        response.encoding = response.apparent_encoding
                    
                    logger.debug(f"Successfully fetched: {url} ({len(response.text)} bytes)")
                    return response.text
                
                elif response.status_code == 403:
                    logger.warning(f"Cloudflare blocked (403): {url}")
                    time.sleep(5)  # Wait before retry
                    continue
                    
                elif response.status_code == 429:
                    logger.warning(f"Rate limited (429): {url}")
                    time.sleep(60)  # Back off for rate limit
                    continue
                    
                else:
                    logger.warning(f"HTTP {response.status_code}: {url}")
                    return None
                    
            except cloudscraper.exceptions.CloudflareChallengeError as e:
                logger.warning(f"Cloudflare challenge failed for {url}: {e}")
                time.sleep(5)
                continue
                
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)
                    continue
                return None
        
        logger.error(f"All retries failed for: {url}")
        return None
    
    def close(self):
        """Close the scraper session."""
        if hasattr(self, 'scraper'):
            self.scraper.close()
            logger.info("CloudscraperClient closed")


# Singleton instance
_cloudscraper_client: Optional[CloudscraperClient] = None


def get_cloudscraper_client() -> CloudscraperClient:
    """Get or create a singleton cloudscraper client."""
    global _cloudscraper_client
    if _cloudscraper_client is None:
        _cloudscraper_client = CloudscraperClient()
    return _cloudscraper_client


def close_cloudscraper_client():
    """Close the singleton cloudscraper client."""
    global _cloudscraper_client
    if _cloudscraper_client:
        _cloudscraper_client.close()
        _cloudscraper_client = None
