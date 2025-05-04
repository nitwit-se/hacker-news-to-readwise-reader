import os
import asyncio
import time
import pathlib
from functools import lru_cache
from typing import List, Dict, Tuple, Optional, Any, Union, cast
from anthropic import Anthropic, AsyncAnthropic

# Initialize the Anthropic clients
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
async_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Import our content extractor
import asyncio
from src.content_extractor import extract_content_from_url

# Default location for prompt template
DEFAULT_PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")
STORY_PROMPT_FILE = os.environ.get("HN_STORY_PROMPT_FILE", os.path.join(DEFAULT_PROMPTS_DIR, "story_relevance.txt"))

# Default prompt template as fallback
DEFAULT_STORY_PROMPT = """I am the CTO for a post series-A startup with a SaaS product modelling climate mitigation plans for cities. As CTO it is my job to stay on top of all relevant news for my job, as well as nurturing my technical / hacker interests.

You are my personal content classifier for Hacker News stories. Your task is to determine if a story is likely to be of interest to me based on the information provided, which may include title, URL, and article content.

To help you make a judgement here are some examples of things that interest me as well as things that I know do not interest me. These are examples.

MY INTERESTS:
- Programming and software development
- AI, machine learning, and LLMs
- Linux, Emacs, NixOS
- Computer science theory and algorithms
- Cybersecurity, hacking techniques, and security vulnerabilities
- Science fiction concepts and technology
- Hardware hacking and electronics
- Systems programming and low-level computing
- Novel computing paradigms and research
- Tech history and vintage computing
- Mathematics and computational theory
- Cool toys and gadgetst
- Climate Change and Mitigation

NOT MY INTERESTS:
- Business/startup funding news
- Tech company stock prices or financial performance
- Product announcements (unless truly innovative)
- General tech industry news without technical depth
- Political news (unless directly related to technology policy or climate change)
- General mainstream technology coverage

Rate the story's relevance to these interests on a scale from 0-100, where 0 would be completely uninteresting and 100 would be almost guaranteed to be of interest to me personally or for my work as CTO.

ONLY respond with a single integer between 0 and 100, and nothing else."""

def load_prompt_template(file_path: str, default_template: str) -> str:
    """Load a prompt template from a file, with fallback to default template.
    
    Args:
        file_path (str): Path to the prompt template file
        default_template (str): Default template to use if file cannot be loaded
        
    Returns:
        str: The loaded template or default if file cannot be loaded
    """
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                template = f.read()
                print(f"Loaded prompt template from {file_path}")
                return template
        else:
            print(f"WARNING: Prompt template file {file_path} not found. Using built-in default template.")
            print("If you intended to use a custom prompt file, please check the file path.")
            return default_template
    except Exception as e:
        print(f"ERROR: Failed to load prompt template from {file_path}: {e}")
        print("Using built-in default template instead. If you intended to use a custom prompt file, please check the file permissions and format.")
        return default_template

# Load prompt template when module is imported
STORY_PROMPT_TEMPLATE = load_prompt_template(STORY_PROMPT_FILE, DEFAULT_STORY_PROMPT)

def get_relevance_score(story: Dict[str, Any], use_content_extraction: bool = False) -> int:
    """Calculate a relevance score for how well a HN story matches user interests.
    
    Args:
        story (Dict[str, Any]): Story details from the Hacker News API
        use_content_extraction (bool): Whether to extract and use article content
        
    Returns:
        int: Relevance score from 0-100, where higher values indicate more relevant content
    """
    title = story.get('title', '')
    url = story.get('url', '')
    
    # Extract domain if URL is available
    domain = ""
    if url and '://' in url:
        domain = url.split('://')[1].split('/')[0]
    
    # Extract content if enabled and URL is available
    article_content = ""
    if use_content_extraction and url:
        try:
            # Run content extraction in a new event loop if we're not already in one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Use an executor if we're already in an event loop
                    content = asyncio.run_coroutine_threadsafe(
                        extract_content_from_url(url),
                        loop
                    ).result(timeout=60)  # 60 second timeout
                else:
                    # If we're not in an event loop, create one
                    content = asyncio.run(extract_content_from_url(url))
                
                if content:
                    # Limit content length to avoid token limits
                    article_content = content[:5000] if len(content) > 5000 else content
            except Exception as e:
                print(f"Error extracting content from {url}: {e}")
        except Exception as e:
            print(f"Unexpected error in content extraction: {e}")
    
    # Construct prompt with all available information
    prompt = f"Title: {title}\nDomain: {domain}\nURL: {url}"
    
    # Add article content if available
    if article_content:
        prompt += f"\n\nArticle Content:\n{article_content}"
    
    # Use the loaded story prompt template
    system_prompt = STORY_PROMPT_TEMPLATE
    
    # Call Claude API to classify
    try:
        message = client.messages.create(
            model="claude-3-5-haiku-latest",  # Using Claude 3.5 Haiku for better results
            max_tokens=100,                   # Tokens for response
            temperature=0,                    # No randomness for consistent results
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response - this assumes Claude follows instructions and returns a number
        response = message.content[0].text.strip()
        try:
            score = int(response)
            # Ensure the score is within the valid range
            return max(0, min(100, score))
        except ValueError:
            # If we couldn't parse an integer, make a best effort to continue
            if "not relevant" in response.lower():
                return 0
            elif "highly relevant" in response.lower():
                return 90
            elif "moderately relevant" in response.lower():
                return 60
            elif "slightly relevant" in response.lower():
                return 30
            else:
                return 0
        
    except Exception as e:
        # Log error and raise the exception instead of returning 0
        # This will prevent the caller from getting a default value when the API fails
        print(f"Error calculating relevance score: {e}")
        raise

# Keep the old function for backward compatibility, but use the new one internally
def is_interesting(story: Dict[str, Any], threshold: int = 75, use_content_extraction: bool = False) -> bool:
    """Classify if a HN story matches user interests using a relevance score.
    
    Args:
        story (Dict[str, Any]): Story details from the Hacker News API
        threshold (int): Minimum relevance score to be considered interesting (0-100)
        use_content_extraction (bool): Whether to extract and use article content
        
    Returns:
        bool: True if the story's relevance score exceeds the threshold
    """
    # If we already have a stored relevance score, use it
    if 'relevance_score' in story and story['relevance_score'] is not None:
        return story['relevance_score'] >= threshold
    
    # Otherwise, calculate a new score
    try:
        score = get_relevance_score(story, use_content_extraction=use_content_extraction)
        
        # Store the score in the story dictionary for potential later use
        story['relevance_score'] = score
        
        return score >= threshold
    except Exception as e:
        # If relevance scoring fails, don't modify the story's relevance_score
        print(f"Could not determine if story {story.get('id')} is interesting: {e}")
        # Return False as we can't determine if it's interesting
        return False

@lru_cache(maxsize=128)
def get_domain_relevance_score(domain: str) -> int:
    """Calculate a relevance score for a domain, with caching.
    
    DEPRECATED: This function now uses the story prompt template instead
    of a separate domain template. It's maintained for backward compatibility.
    
    Args:
        domain (str): The website domain
        
    Returns:
        int: Relevance score from 0-100
    """
    # Use a synthetic story with just the domain
    synthetic_story = {
        "title": f"Story from {domain}",
        "url": f"https://{domain}"
    }
    
    # Use the main relevance scoring function
    try:
        return get_relevance_score(synthetic_story, use_content_extraction=False)
    except Exception as e:
        print(f"Error calculating domain relevance score for {domain}: {e}")
        raise

async def get_relevance_score_async(story: Dict[str, Any], use_content_extraction: bool = False) -> int:
    """Asynchronous version of get_relevance_score.
    
    Args:
        story (Dict[str, Any]): Story details from the Hacker News API
        use_content_extraction (bool): Whether to extract and use article content
        
    Returns:
        int: Relevance score from 0-100
    """
    title = story.get('title', '')
    url = story.get('url', '')
    
    # Extract domain if URL is available
    domain = ""
    if url and '://' in url:
        domain = url.split('://')[1].split('/')[0]
        
    # Always perform full story analysis regardless of domain
    
    # Extract content if enabled and URL is available
    article_content = ""
    if use_content_extraction and url:
        try:
            # We can directly await since we're already in an async context
            content = await extract_content_from_url(url)
            if content:
                # Limit content length to avoid token limits
                article_content = content[:5000] if len(content) > 5000 else content
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
    
    # Construct prompt with all available information
    prompt = f"Title: {title}\nDomain: {domain}\nURL: {url}"
    
    # Add article content if available
    if article_content:
        prompt += f"\n\nArticle Content:\n{article_content}"
    
    # Use the loaded story prompt template
    system_prompt = STORY_PROMPT_TEMPLATE
    
    # Call Claude API to classify
    try:
        message = await async_client.messages.create(
            model="claude-3-5-haiku-latest",  # Using Claude 3.5 Haiku for better results
            max_tokens=100,                   # Tokens for response
            temperature=0,                    # No randomness for consistent results
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse the response
        response = message.content[0].text.strip()
        try:
            score = int(response)
            # Ensure the score is within the valid range
            return max(0, min(100, score))
        except ValueError:
            # Make a best effort to continue if parsing fails
            if "not relevant" in response.lower():
                return 0
            elif "highly relevant" in response.lower():
                return 90
            elif "moderately relevant" in response.lower():
                return 60
            elif "slightly relevant" in response.lower():
                return 30
            else:
                return 0
    except Exception as e:
        # Log error and raise the exception instead of returning 0
        print(f"Error calculating relevance score asynchronously: {e}")
        raise

async def process_story_batch_async(stories: List[Dict[str, Any]], throttle_delay: float = 0.2, use_content_extraction: bool = False) -> List[Dict[str, Any]]:
    """Process a batch of stories asynchronously to get relevance scores.
    
    Args:
        stories (List[Dict[str, Any]]): List of story dictionaries to process
        throttle_delay (float): Delay between API calls to avoid rate limits
        use_content_extraction (bool): Whether to extract and use article content
        
    Returns:
        List[Dict[str, Any]]: List of stories with added relevance scores
    """
    tasks = []
    
    for i, story in enumerate(stories):
        # Add throttling delay to avoid hitting rate limits
        # Space out the calls slightly for better API behavior
        await asyncio.sleep(throttle_delay * i)
        task = asyncio.create_task(get_relevance_score_async(story, use_content_extraction=use_content_extraction))
        tasks.append((story, task))
    
    # Wait for all tasks to complete and update stories
    for story, task in tasks:
        try:
            story['relevance_score'] = await task
        except Exception as e:
            print(f"Error processing story {story.get('id')}: {e}")
            # Don't set relevance_score to 0 on API failure - leave it unchanged
            # Only set it if it doesn't exist yet in the story
            if 'relevance_score' not in story:
                story['relevance_score'] = None
    
    return stories
