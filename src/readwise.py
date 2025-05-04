"""
Readwise Reader API integration for HN Poller.
Handles checking and adding URLs to Readwise Reader.
"""

import os
import time
from typing import Dict, List, Optional, Tuple, Any
import requests
from requests.exceptions import RequestException
import backoff

# API constants
READWISE_API_URL = "https://readwise.io/api/v3"
LIST_ENDPOINT = f"{READWISE_API_URL}/list/"
SAVE_ENDPOINT = f"{READWISE_API_URL}/save/"

class ReadwiseError(Exception):
    """Exception raised for Readwise API errors."""
    pass

def get_api_key() -> str:
    """Get Readwise API key from environment variable."""
    api_key = os.environ.get("READWISE_API_KEY")
    if not api_key:
        raise ReadwiseError("READWISE_API_KEY environment variable not set")
    return api_key

def get_headers() -> Dict[str, str]:
    """Get HTTP headers for Readwise API requests."""
    return {
        "Authorization": f"Token {get_api_key()}",
        "Content-Type": "application/json",
    }

@backoff.on_exception(
    backoff.expo,
    (RequestException, ReadwiseError),
    max_tries=5, 
    giveup=lambda e: "404" in str(e),  # Don't retry on 404 errors
    factor=2,
    jitter=backoff.full_jitter
)
def fetch_readwise_page(page_cursor: Optional[str] = None, limit: int = 250) -> Dict[str, Any]:
    """
    Fetch a single page of documents from Readwise Reader API.
    Uses exponential backoff for retries on failure.
    
    Args:
        page_cursor: Cursor for pagination 
        limit: Number of items per page
        
    Returns:
        Dict containing response data
        
    Raises:
        ReadwiseError: If the API request fails after retries
    """
    params = {"limit": limit}
    
    if page_cursor:
        params["pageCursor"] = page_cursor
        
    try:
        response = requests.get(
            LIST_ENDPOINT,
            headers=get_headers(),
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    except RequestException as e:
        # Handle rate limiting specially
        if "429" in str(e):
            # Get retry-after header if available
            retry_after = None
            if hasattr(e, 'response') and e.response is not None:
                retry_after = e.response.headers.get('Retry-After')
            
            error_msg = "Rate limit exceeded."
            if retry_after:
                error_msg += f" Retry after {retry_after} seconds."
            
            raise ReadwiseError(error_msg)
        
        raise ReadwiseError(f"Failed to fetch documents from Readwise: {str(e)}")

def get_all_readwise_urls() -> set:
    """
    Fetches all documents from Readwise Reader and extracts their source URLs.
    Uses pagination and retry logic to handle rate limits.
    
    Returns:
        set: A set of all source URLs in Readwise Reader
    
    Raises:
        ReadwiseError: If the API request fails after retries
    """
    all_urls = set()
    page_cursor = None
    page_num = 1
    
    try:
        # Paginate through results
        while True:
            print(f"Fetching page {page_num} of documents from Readwise Reader...")
            
            # Use our retry-enabled function
            data = fetch_readwise_page(page_cursor=page_cursor, limit=250)
            
            results = data.get("results", [])
            print(f"Got {len(results)} documents on this page")
            
            # Extract source URLs from results and add to set
            for result in results:
                if result.get("source_url"):
                    all_urls.add(result.get("source_url"))
            
            # Check if there are more pages
            page_cursor = data.get("nextPageCursor")
            if not page_cursor:
                break
            
            # Pause briefly between pages to reduce load
            time.sleep(0.5)
            page_num += 1
            
        return all_urls
        
    except ReadwiseError as e:
        # Propagate the error with context
        raise ReadwiseError(f"Error fetching documents from Readwise Reader: {str(e)}")

def url_exists_in_readwise(url: str, existing_urls: Optional[set] = None) -> bool:
    """
    Check if a URL already exists in Readwise Reader.
    
    Args:
        url: The URL to check
        existing_urls: Optional set of URLs already in Readwise Reader
            If provided, checks against this set; otherwise fetches from API
        
    Returns:
        True if the URL exists, False otherwise
    
    Raises:
        ReadwiseError: If the API request fails when fetching URLs
    """
    if existing_urls is None:
        existing_urls = get_all_readwise_urls()
        
    return url in existing_urls

@backoff.on_exception(
    backoff.expo,
    (RequestException, ReadwiseError),
    max_tries=3,
    giveup=lambda e: "404" in str(e),  # Don't retry on 404 errors
    factor=2,
    jitter=backoff.full_jitter
)
def add_to_readwise(
    url: str, 
    title: str, 
    source: str = "hn-poll"
) -> Dict[str, Any]:
    """
    Add a URL to Readwise Reader with retry logic.
    
    Args:
        url: The URL to add
        title: The title for the URL
        source: Source tag for the URL
        
    Returns:
        The API response data
        
    Raises:
        ReadwiseError: If the API request fails after retries
    """
    try:
        payload = {
            "url": url,
            "title": title,
            "author": source,
            "tags": ["hackernews"],
            "should_clean_html": True,
        }
        
        print(f"Adding to Readwise Reader: {title}")
        response = requests.post(
            SAVE_ENDPOINT,
            headers=get_headers(),
            json=payload
        )
        response.raise_for_status()
        return response.json()
        
    except RequestException as e:
        # Handle rate limiting specially
        if "429" in str(e):
            # Get retry-after header if available
            retry_after = None
            if hasattr(e, 'response') and e.response is not None:
                retry_after = e.response.headers.get('Retry-After')
            
            error_msg = "Rate limit exceeded when adding URL."
            if retry_after:
                error_msg += f" Retry after {retry_after} seconds."
            
            raise ReadwiseError(error_msg)
        
        raise ReadwiseError(f"Failed to add URL to Readwise: {str(e)}")

# Import get_story function at the module level to avoid circular imports
# This is imported here rather than at the top to avoid circular imports
from src.api import get_story

def batch_add_to_readwise(
    stories: List[Dict[str, Any]], 
    source: str = "hn-poll",
    existing_urls: Optional[set] = None,
    verify_story_exists: bool = True
) -> Tuple[List[int], List[Tuple[int, str]]]:
    """
    Add multiple stories to Readwise Reader, checking for existence first.
    
    Args:
        stories: List of story dictionaries with 'id', 'url', and 'title'
        source: Source tag for the URLs
        existing_urls: Optional set of URLs already in Readwise Reader
            If provided, checks against this set; otherwise fetches from API
        verify_story_exists: Verify that each story actually exists on HN before syncing
        
    Returns:
        Tuple of (successfully_added_ids, failed_ids_with_errors)
    """
    added_ids = []
    failed_ids = []
    
    # If no existing URLs provided, work with an empty set
    if existing_urls is None:
        existing_urls = set()
    
    for story in stories:
        story_id = story.get("id")
        url = story.get("url", "")
        title = story.get("title", "")
        
        # Ensure we have a valid story ID
        if not story_id:
            failed_ids.append((0, "Missing story ID"))
            continue
        
        # Verify the story actually exists on Hacker News
        if verify_story_exists:
            # Use the HN API to check if the story exists
            hn_story = get_story(story_id)
            if not hn_story:
                error_msg = "Story does not exist on Hacker News"
                print(f"Error adding story (ID: {story_id}): {error_msg}")
                failed_ids.append((story_id, error_msg))
                continue
            
            # If we successfully found the story, update our local copy with its details
            if not url or url.strip() == "":
                url = hn_story.get("url", "")
            if not title or title.strip() == "":
                title = hn_story.get("title", "")
        
        # Generate a fallback URL for Ask HN posts or text posts that don't have URLs
        if not url or url.strip() == "":
            url = f"https://news.ycombinator.com/item?id={story_id}"
            print(f"Using HN fallback URL for story ID {story_id}")
        
        # Ensure we have a title
        if not title or title.strip() == "":
            # Try to generate a basic title if missing
            title = f"Hacker News story {story_id}"
            print(f"Using fallback title for story ID {story_id}")
        
        try:
            # Check if URL already exists using our pre-fetched set
            if url in existing_urls:
                # URL exists but we still count it as added for tracking purposes
                added_ids.append(story_id)
                print(f"Skipping already saved URL: {url}")
                continue
                
            # Add to Readwise with retry logic
            add_to_readwise(url, title, source)
            added_ids.append(story_id)
            
            # Also add to our local set to avoid re-checking
            existing_urls.add(url)
            
            # Avoid rate limiting
            time.sleep(1)  # Increased to be more conservative
            
        except ReadwiseError as e:
            error_msg = str(e)
            print(f"Error adding story (ID: {story_id}): {error_msg}")
            failed_ids.append((story_id, error_msg))
            # Wait longer after an error to avoid cascading failures
            time.sleep(2)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Error adding story (ID: {story_id}): {error_msg}")
            failed_ids.append((story_id, error_msg))
            # Wait longer after an error to avoid cascading failures
            time.sleep(2)
            
    return added_ids, failed_ids