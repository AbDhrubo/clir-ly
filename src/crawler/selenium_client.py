"""
Selenium-based browser client for sites with Cloudflare/WAF protection.

This module provides a browser-based alternative to the requests-based
HttpClient for sites that block automated requests.
"""

import logging
import time
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class SeleniumClient:
    """
    Browser-based HTTP client using Selenium for Cloudflare-protected sites.
    
    This client uses a headless Chrome browser to bypass bot detection.
    """
    
    def __init__(
        self,
        headless: bool = True,
        delay: float = 2.0,
        timeout: int = 30,
    ):
        """
        Initialize the Selenium client.
        
        Args:
            headless: Run browser in headless mode (no UI)
            delay: Delay between requests in seconds
            timeout: Page load timeout in seconds
        """
        self.headless = headless
        self.delay = delay
        self.timeout = timeout
        self._driver: Optional[webdriver.Chrome] = None
        self._last_request_time = 0
    
    def _get_driver(self) -> webdriver.Chrome:
        """Get or create the Chrome WebDriver instance."""
        if self._driver is None:
            options = Options()
            
            if self.headless:
                options.add_argument("--headless=new")
            
            # Anti-detection options
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Disable automation flags
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            
            try:
                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(service=service, options=options)
                self._driver.set_page_load_timeout(self.timeout)
                
                # Execute CDP commands to hide webdriver
                self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    """
                })
                
                logger.info("Selenium WebDriver initialized")
            except Exception as e:
                logger.error(f"Failed to initialize WebDriver: {e}")
                raise
        
        return self._driver
    
    def _rate_limit(self):
        """Apply rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
    
    def get(self, url: str, wait_for_element: Optional[str] = None) -> Optional[str]:
        """
        Fetch a URL using the browser.
        
        Args:
            url: URL to fetch
            wait_for_element: Optional CSS selector to wait for
            
        Returns:
            HTML content as string, or None if request failed
        """
        self._rate_limit()
        
        try:
            driver = self._get_driver()
            logger.debug(f"Fetching with browser: {url}")
            
            driver.get(url)
            self._last_request_time = time.time()
            
            # Wait for Cloudflare challenge if present
            time.sleep(3)  # Allow time for any challenges
            
            # Wait for specific element if requested
            if wait_for_element:
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                    )
                except TimeoutException:
                    logger.warning(f"Element {wait_for_element} not found on {url}")
            
            return driver.page_source
            
        except TimeoutException:
            logger.warning(f"Timeout loading {url}")
            return None
        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def close(self):
        """Close the browser and clean up resources."""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("Selenium WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self._driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


# Singleton instance for reuse
_selenium_client: Optional[SeleniumClient] = None


def get_selenium_client(headless: bool = True) -> SeleniumClient:
    """Get or create a singleton Selenium client instance."""
    global _selenium_client
    if _selenium_client is None:
        _selenium_client = SeleniumClient(headless=headless)
    return _selenium_client


def close_selenium_client():
    """Close the singleton Selenium client."""
    global _selenium_client
    if _selenium_client:
        _selenium_client.close()
        _selenium_client = None
