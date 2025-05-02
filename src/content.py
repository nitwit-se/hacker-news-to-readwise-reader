import requests
import html2text
from bs4 import BeautifulSoup
import time
import logging
import random
from urllib.parse import urlparse
from functools import wraps

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('hn_content')

class ContentFetchError(Exception):
    """Exception raised for content fetching errors."""
    def __init__(self, url, error_type, message, status_code=None):
        self.url = url
        self.error_type = error_type
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)
    
    def __str__(self):
        return f"{self.error_type} for {self.url}: {self.message} (status: {self.status_code})"

def retry_with_backoff(max_retries=3, initial_backoff=1, max_backoff=10):
    """Retry a function with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            backoff = initial_backoff
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.Timeout:
                    # Always retry timeouts
                    pass
                except requests.exceptions.ConnectionError:
                    # Always retry connection errors
                    pass
                except requests.exceptions.HTTPError as e:
                    # Only retry specific status codes (e.g., 429, 500, 502, 503, 504)
                    if e.response.status_code not in (429, 500, 502, 503, 504):
                        raise
                except Exception as e:
                    # Don't retry other exceptions
                    raise
                
                if retries == max_retries:
                    # We've run out of retries, raise the last exception
                    raise
                
                # Calculate backoff with jitter
                jitter = random.uniform(0, 0.1 * backoff)
                sleep_time = backoff + jitter
                
                logger.info(f"Retry {retries + 1}/{max_retries} for {args[0]} in {sleep_time:.2f}s")
                time.sleep(sleep_time)
                
                # Increase backoff for next retry
                retries += 1
                backoff = min(backoff * 2, max_backoff)
                
        return wrapper
    return decorator

# List of problematic domains that need special handling
PROBLEMATIC_DOMAINS = {
    'twitter.com': 'Twitter blocks most scraping attempts',
    'x.com': 'Twitter (X) blocks most scraping attempts',
    't.co': 'Twitter shortlink service blocks most scraping attempts',
    'instagram.com': 'Instagram blocks most scraping attempts',
    'facebook.com': 'Facebook blocks most scraping attempts',
    'linkedin.com': 'LinkedIn blocks most scraping attempts',
}

@retry_with_backoff(max_retries=2)
def fetch_url_content(url, timeout=10):
    """Fetch content from a URL with improved error handling.
    
    Args:
        url (str): The URL to fetch
        timeout (int): Request timeout in seconds
        
    Returns:
        str or None: HTML content if successful, None otherwise
        
    Raises:
        ContentFetchError: When content cannot be fetched
    """
    if not url:
        logger.warning("Empty URL provided")
        return None
        
    # Skip URLs that are likely to be problematic
    parsed_url = urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        logger.warning(f"Invalid URL format: {url}")
        raise ContentFetchError(url, "InvalidURL", "URL is missing scheme or domain")
    
    # Check for problematic domains
    domain = parsed_url.netloc.lower()
    if domain.startswith('www.'):
        domain = domain[4:]
    
    for problematic_domain, reason in PROBLEMATIC_DOMAINS.items():
        if problematic_domain in domain:
            logger.info(f"Skipping known problematic domain {domain}: {reason}")
            raise ContentFetchError(url, "ProblematicDomain", reason)
    
    # Vary user agent slightly to avoid detection
    user_agents = [
        'Mozilla/5.0 (compatible; HackerNewsPoller/0.1; +https://github.com/example/hn-poller)',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/91.0.4472.114 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/92.0.4515.107 Safari/537.36',
    ]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
    }
    
    try:
        logger.info(f"Fetching content from {url}")
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # Handle specific status codes
        if response.status_code == 200:
            return response.text
        elif response.status_code == 404:
            raise ContentFetchError(url, "NotFound", "Page not found", status_code=404)
        elif response.status_code == 403:
            raise ContentFetchError(url, "Forbidden", "Access forbidden", status_code=403)
        elif response.status_code == 429:
            raise ContentFetchError(url, "RateLimited", "Too many requests", status_code=429)
        else:
            response.raise_for_status()  # This will raise HTTPError for other status codes
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout error fetching {url}")
        raise ContentFetchError(url, "Timeout", f"Request timed out after {timeout}s")
    except requests.exceptions.TooManyRedirects:
        logger.warning(f"Too many redirects for {url}")
        raise ContentFetchError(url, "TooManyRedirects", "Too many redirects")
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error for {url}: {str(e)}")
        raise ContentFetchError(url, "ConnectionError", str(e))
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error for {url}: {str(e)}")
        raise ContentFetchError(url, "HTTPError", str(e), status_code=e.response.status_code)
    except (UnicodeDecodeError, UnicodeError) as e:
        logger.warning(f"Unicode decode error for {url}: {str(e)}")
        raise ContentFetchError(url, "UnicodeError", str(e))
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {str(e)}")
        raise ContentFetchError(url, "UnexpectedError", str(e))

def html_to_markdown(html_content):
    """Convert HTML content to markdown.
    
    Args:
        html_content (str): HTML content to convert
        
    Returns:
        str or None: Markdown content if successful, None otherwise
    """
    if not html_content:
        return None
        
    try:
        # First use BeautifulSoup to clean up the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "aside"]):
            script.extract()
        
        # Get text content
        text = soup.get_text()
        
        # Convert to markdown using html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # No wrapping
        markdown = h.handle(str(soup))
        
        return markdown
    except Exception as e:
        print(f"Error converting HTML to markdown: {e}")
        return None

def get_content_summary(markdown, max_chars=200):
    """Get a summary of markdown content.
    
    Args:
        markdown (str): Markdown content
        max_chars (int): Maximum characters to include
        
    Returns:
        str: Summary of content
    """
    if not markdown:
        return ""
        
    # Remove extra whitespace and newlines
    cleaned = ' '.join(markdown.split())
    
    # Truncate to max_chars
    if len(cleaned) > max_chars:
        return cleaned[:max_chars] + "..."
    return cleaned

def fetch_and_process_content(url):
    """Fetch URL content and convert to markdown.
    
    Args:
        url (str): The URL to fetch and process
        
    Returns:
        tuple: (markdown content, summary)
        
    Raises:
        ContentFetchError: When content cannot be fetched or processed
    """
    try:
        html_content = fetch_url_content(url)
        if not html_content:
            # This should never happen now that fetch_url_content raises exceptions
            # but keeping as a failsafe
            logger.warning(f"Empty HTML content returned for {url}")
            return None, None
            
        markdown = html_to_markdown(html_content)
        if not markdown:
            logger.warning(f"HTML to markdown conversion failed for {url}")
            raise ContentFetchError(url, "ConversionError", "Failed to convert HTML to markdown")
            
        summary = get_content_summary(markdown)
        
        return markdown, summary
    except ContentFetchError:
        # Pass through ContentFetchError exceptions
        raise
    except Exception as e:
        # Wrap other exceptions in ContentFetchError
        logger.error(f"Error in fetch_and_process_content for {url}: {str(e)}", exc_info=True)
        raise ContentFetchError(url, "ProcessingError", str(e))

def process_story_batch(stories, delay=1.0):
    """Process a batch of stories to get their content.
    
    Args:
        stories (list): List of story dictionaries with id and url
        delay (float): Delay between requests to avoid rate limiting
        
    Returns:
        list: List of processed stories with content added or error information
    """
    processed = []
    
    for story in stories:
        if not story.get('url'):
            continue
            
        try:
            markdown, summary = fetch_and_process_content(story['url'])
            if markdown:
                story['content'] = markdown
                story['content_summary'] = summary
                story['content_fetched'] = 1
                story['error'] = None
                processed.append(story)
                logger.info(f"Successfully processed content for story ID {story['id']}")
            else:
                # Content was None but no exception was raised
                story['error_type'] = 'EmptyContent'
                story['error_message'] = 'No content could be extracted'
                story['content_fetched'] = 2  # Mark as attempted but failed
                processed.append(story)
                logger.warning(f"No content extracted for story ID {story['id']} (URL: {story['url']})")
        except ContentFetchError as e:
            # Handle the content fetch error
            story['error_type'] = e.error_type
            story['error_message'] = e.message
            story['error_status'] = e.status_code
            story['content_fetched'] = 2  # Mark as attempted but failed
            processed.append(story)
            logger.warning(f"Content fetch error for story ID {story['id']}: {e}")
        except Exception as e:
            # Handle unexpected errors
            story['error_type'] = 'UnexpectedError'
            story['error_message'] = str(e)
            story['content_fetched'] = 2  # Mark as attempted but failed
            processed.append(story)
            logger.error(f"Unexpected error processing story ID {story['id']}: {e}", exc_info=True)
        finally:
            # Add a delay to avoid hammering websites
            time.sleep(delay)
    
    return processed