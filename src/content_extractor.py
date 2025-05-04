import asyncio
import time
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse
import logging

# Third-party imports
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
import trafilatura

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentExtractor:
    """A class for extracting content from web pages using Playwright and Trafilatura.
    
    This class handles the extraction of text content from web articles, bypassing most
    anti-scraping measures through the use of a headless browser, and then extracting
    the main content using Trafilatura for readability.
    """
    
    def __init__(self, timeout: int = 30, headless: bool = True):
        """Initialize the ContentExtractor.
        
        Args:
            timeout (int): Timeout for page loading in seconds
            headless (bool): Whether to run the browser in headless mode
        """
        self.timeout = timeout * 1000  # Convert to milliseconds
        self.headless = headless
        self._browser = None
        self._context = None
        
    async def _initialize_browser(self) -> None:
        """Initialize the browser if it doesn't exist."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=self.headless)
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
            )
        
    async def _close_browser(self) -> None:
        """Close the browser and playwright instance if it exists."""
        if self._browser:
            await self._context.close()
            await self._browser.close()
            self._browser = None
            self._context = None
    
    async def extract_content(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract content from a URL.
        
        Args:
            url (str): The URL to extract content from
            
        Returns:
            Tuple[Optional[str], Optional[str]]: The raw HTML and extracted text content
        """
        if not url or not url.startswith(('http://', 'https://')):
            return None, None
            
        try:
            await self._initialize_browser()
            page = await self._context.new_page()
            
            # Navigate to the URL with timeout
            logger.info(f"Navigating to {url}")
            await page.goto(url, timeout=self.timeout, wait_until="networkidle")
            
            # Wait for the content to be fully loaded
            await asyncio.sleep(1)  # Small additional delay for dynamic content
            
            # Get HTML content
            html = await page.content()
            
            # Close the page
            await page.close()
            
            # Extract main content using Trafilatura
            text_content = trafilatura.extract(
                html,
                output_format="markdown",
                include_links=True,
                include_images=False,
                favor_precision=True
            )
            
            return html, text_content
            
        except PlaywrightTimeoutError:
            logger.warning(f"Timeout while loading {url}")
            return None, None
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None, None
            
    async def extract_content_batch(self, urls: List[str], 
                               max_concurrent: int = 3) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
        """Extract content from multiple URLs concurrently.
        
        Args:
            urls (List[str]): List of URLs to extract content from
            max_concurrent (int): Maximum number of concurrent extractions
            
        Returns:
            Dict[str, Tuple[Optional[str], Optional[str]]]: Dictionary mapping URLs to their content
        """
        results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_semaphore(url):
            async with semaphore:
                # Add random delay between requests to be less aggressive
                await asyncio.sleep(0.5 + (hash(url) % 100) / 100)
                return url, await self.extract_content(url)
        
        # Create tasks for all URLs
        tasks = [extract_with_semaphore(url) for url in urls]
        
        try:
            # Wait for all tasks to complete
            for completed_task in asyncio.as_completed(tasks):
                url, content = await completed_task
                results[url] = content
        except Exception as e:
            logger.error(f"Error in batch extraction: {e}")
        finally:
            # Ensure browser is closed
            await self._close_browser()
            
        return results

    async def __aenter__(self):
        """Initialize browser when used as a context manager."""
        await self._initialize_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close browser when exiting context manager."""
        await self._close_browser()

async def extract_content_from_url(url: str) -> Optional[str]:
    """Extract content from a URL and return as markdown text.
    
    Args:
        url (str): The URL to extract content from
        
    Returns:
        Optional[str]: The extracted content as markdown text, or None if extraction failed
    """
    async with ContentExtractor() as extractor:
        _, text_content = await extractor.extract_content(url)
        return text_content