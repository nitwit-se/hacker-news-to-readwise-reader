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
    # Social media sites
    'twitter.com': 'Twitter blocks most scraping attempts',
    'x.com': 'Twitter (X) blocks most scraping attempts',
    't.co': 'Twitter shortlink service blocks most scraping attempts',
    'instagram.com': 'Instagram blocks most scraping attempts',
    'facebook.com': 'Facebook blocks most scraping attempts',
    'linkedin.com': 'LinkedIn blocks most scraping attempts',
    
    # Common paywalled news sites
    'wsj.com': 'Content behind paywall (Wall Street Journal)',
    'economist.com': 'Content behind paywall (The Economist)',
    'nytimes.com': 'Content behind paywall (New York Times)',
    'ft.com': 'Content behind paywall (Financial Times)',
    'washingtonpost.com': 'Content behind paywall (Washington Post)',
    'bloomberg.com': 'Content behind paywall (Bloomberg)',
    'newyorker.com': 'Content behind paywall (The New Yorker)',
    'wired.com': 'Content behind paywall (Wired)',
    'medium.com': 'May have metered paywall (Medium)',
    'substack.com': 'May have subscription requirements (Substack)',
    
    # Sites with strong anti-scraping measures
    'phys.org': 'Site implements anti-scraping protection',
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
    
    # More realistic and recent user agents to better evade detection
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/122.0.2365.92',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    ]
    
    # More complete headers that mimic a real browser
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'DNT': '1',
    }
    
    try:
        logger.info(f"Fetching content from {url}")
        response = requests.get(url, headers=headers, timeout=timeout)
        
        # Handle specific status codes
        if response.status_code == 200:
            return response.text
        elif response.status_code == 402:
            raise ContentFetchError(url, "PaywallError", "Content behind paywall or subscription required", status_code=402)
        elif response.status_code == 404:
            raise ContentFetchError(url, "NotFound", "Page not found", status_code=404)
        elif response.status_code == 403:
            raise ContentFetchError(url, "Forbidden", "Access forbidden", status_code=403)
        elif response.status_code == 422:
            raise ContentFetchError(url, "ContentError", "Server rejected request - possibly bot protection", status_code=422)
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
    """Convert HTML content to markdown, extracting main article content.
    
    Args:
        html_content (str): HTML content to convert
        
    Returns:
        str or None: Markdown content if successful, None otherwise
    """
    if not html_content:
        return None
        
    try:
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove non-content elements - expanded to include more technical elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript', 
                                      'iframe', 'svg', 'canvas', 'code', 'pre', 'form', 'button',
                                      'input', 'select', 'option', 'textarea']):
            element.decompose()
            
        # Remove common ad/nav class patterns - expanded to include code-related classes
        import re
        for element in soup.find_all(class_=re.compile('(nav|menu|header|footer|sidebar|banner|ad|widget|cookie|popup|social|comment|code|syntax|highlight|editor|terminal|console|snippet|gist)')):
            element.decompose()
            
        # Remove elements with common advertisement/tracking attribute patterns
        for element in soup.find_all(attrs={"id": re.compile('(ad|banner|promo|sponsor|comment|reply|code|snippet|gist)')}):
            element.decompose()
            
        # Remove elements with data-ad attributes and other common ad-related attributes
        for element in soup.find_all(lambda tag: any(attr for attr in tag.attrs if attr.startswith('data-') and ('ad' in attr or 'track' in attr or 'analytics' in attr))):
            element.decompose()
            
        # Find the main content
        # Strategies in priority order:
        main_content = None
        
        # 1. Look for common content containers
        for selector in ['article', 'main', '.content', '#content', '.post', '.entry', '.article', '[role="main"]']:
            try:
                content_element = soup.select_one(selector)
                if content_element and len(content_element.get_text(strip=True)) > 200:  # At least 200 chars
                    main_content = content_element
                    break
            except Exception:
                continue
        
        # 2. If no content container found, use heuristic to find the div with most text
        if not main_content:
            max_text_length = 0
            best_div = None
            for div in soup.find_all('div'):
                text_length = len(div.get_text(strip=True))
                if text_length > max_text_length and text_length > 200:  # At least 200 chars
                    max_text_length = text_length
                    best_div = div
            
            if best_div:
                main_content = best_div
        
        # Get content as HTML
        if main_content:
            logger.info("Found main content element")
            content_html = str(main_content)
        else:
            logger.info("No main content found, using body")
            content_html = str(soup.body) if soup.body else str(soup)
        
        # Convert to markdown using html2text
        h = html2text.HTML2Text()
        h.ignore_links = True  # Strip out links, keeping only the text
        h.ignore_images = False
        h.body_width = 0  # No wrapping
        markdown = h.handle(content_html)
        
        # Post-process markdown - remove excessive blank lines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown
    except Exception as e:
        logger.error(f"Error converting HTML to markdown: {e}")
        return None

def clean_markdown_content(markdown):
    """Clean and filter markdown content to remove unnecessary elements.
    
    Args:
        markdown (str): Raw markdown content
        
    Returns:
        str: Cleaned markdown content
    """
    if not markdown:
        return ""
    
    import re
    
    # Remove any reference-style links that might appear at the end
    markdown = re.sub(r'\n\[\d+\]: http[^\n]+', '', markdown)
    
    # Remove navigation/footer links (often appear as a series of short links)
    markdown = re.sub(r'(\n\* \[[^\]]{1,20}\]\([^)]+\)){3,}', '', markdown)
    
    # Remove consecutive duplicate link patterns (often navigation menus)
    markdown = re.sub(r'(\[[^\]]+\]\([^)]+\)\s*){3,}', '', markdown)
    
    # Remove social media links
    social_patterns = [
        r'\[[^\]]*(?:Facebook|Twitter|LinkedIn|Instagram|Share|Follow)[^\]]*\]\([^)]+\)',
        r'\[[^\]]*(?:facebook|twitter|linkedin|instagram|share|follow)[^\]]*\]\([^)]+\)'
    ]
    for pattern in social_patterns:
        markdown = re.sub(pattern, '', markdown)
    
    # Remove copyright notices
    markdown = re.sub(r'©\s*\d{4}[^\n]*', '', markdown)
    
    # Remove consecutive short lines (often navigation or footer items)
    lines = markdown.split('\n')
    filtered_lines = []
    
    # Filter out lines that are likely not main content
    for i, line in enumerate(lines):
        # Skip very short lines that appear in groups (often menus)
        if (len(line.strip()) < 30 and i+1 < len(lines) and i+2 < len(lines) and 
            len(lines[i+1].strip()) < 30 and len(lines[i+2].strip()) < 30):
            # But keep headings
            if not line.startswith('#') and not line.startswith('##'):
                continue
                
        # Skip lines that are just separator patterns
        if re.match(r'^[\-\_\*\=\~\+]{3,}$', line.strip()):
            continue
            
        filtered_lines.append(line)
    
    # Join the filtered lines back together
    cleaned_markdown = '\n'.join(filtered_lines)
    
    # Remove excessive blank lines (more than 2 in a row)
    cleaned_markdown = re.sub(r'\n{3,}', '\n\n', cleaned_markdown)
    
    return cleaned_markdown

def get_content_summary(markdown, max_chars=500):
    """Get a summary of markdown content.
    
    Args:
        markdown (str): Markdown content
        max_chars (int): Maximum characters to include
        
    Returns:
        str: Summary of content
    """
    if not markdown:
        return ""
    
    # First clean the markdown content
    cleaned_markdown = clean_markdown_content(markdown)
    
    # Extract the first few paragraphs
    paragraphs = [p for p in cleaned_markdown.split('\n\n') if p.strip()]
    
    # Use the first few paragraphs depending on length
    summary = ""
    for p in paragraphs:
        if len(summary) + len(p) < max_chars * 1.5:  # Allow a bit more than max_chars to get complete paragraphs
            summary += p.strip() + " "
        else:
            break
    
    # Remove markdown formatting from the summary
    import re
    # Remove links, keep text: [text](link) -> text
    summary = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', summary)
    # Remove image references: ![alt](link) -> alt
    summary = re.sub(r'!\[([^\]]+)\]\([^)]+\)', r'\1', summary)
    # Remove formatting markers like * _ ~
    summary = re.sub(r'[*_~]{1,2}([^*_~]+)[*_~]{1,2}', r'\1', summary)
    
    # Remove extra whitespace
    summary = ' '.join(summary.split())
    
    # Truncate to max_chars
    if len(summary) > max_chars:
        return summary[:max_chars] + "..."
    return summary

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
            
        # Convert HTML to markdown with main content extraction
        markdown = html_to_markdown(html_content)
        if not markdown:
            logger.warning(f"HTML to markdown conversion failed for {url}")
            raise ContentFetchError(url, "ConversionError", "Failed to convert HTML to markdown")
            
        # Clean the markdown content to remove navigation, ads, etc.
        cleaned_markdown = clean_markdown_content(markdown)
        
        # Generate a summary from the cleaned content
        summary = get_content_summary(cleaned_markdown)
        
        logger.info(f"Successfully extracted and cleaned content from {url}")
        
        return cleaned_markdown, summary
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