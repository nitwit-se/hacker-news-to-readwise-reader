import os
import asyncio
import time
from functools import lru_cache
from typing import List, Dict, Tuple, Optional, Any, Union, cast
from anthropic import Anthropic, AsyncAnthropic

# Initialize the Anthropic clients
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
async_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def get_relevance_score(story: Dict[str, Any]) -> int:
    """Calculate a relevance score for how well a HN story matches user interests.
    
    Args:
        story (Dict[str, Any]): Story details from the Hacker News API
        
    Returns:
        int: Relevance score from 0-100, where higher values indicate more relevant content
    """
    title = story.get('title', '')
    url = story.get('url', '')
    
    # Extract domain if URL is available
    domain = ""
    if url and '://' in url:
        domain = url.split('://')[1].split('/')[0]
    
    # Construct prompt with all available information
    prompt = f"Title: {title}\nDomain: {domain}\nURL: {url}"
    
    # Interest categories defined in the system prompt
    system_prompt = """You are a personal content classifier for Hacker News stories. Your task is to determine if a story is likely to be of interest to me based ONLY on its title and URL.

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

Rate the story's relevance to these interests on a scale from 0-100, where 0 would be completely uninteresting and 100 would be almost guaranteed to be of interest to me.

ONLY respond with a single integer between 0 and 100, and nothing else."""
    
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
        # Log error and default to 0 if API call fails
        print(f"Error calculating relevance score: {e}")
        return 0

# Keep the old function for backward compatibility, but use the new one internally
def is_interesting(story: Dict[str, Any], threshold: int = 75) -> bool:
    """Classify if a HN story matches user interests using a relevance score.
    
    Args:
        story (Dict[str, Any]): Story details from the Hacker News API
        threshold (int): Minimum relevance score to be considered interesting (0-100)
        
    Returns:
        bool: True if the story's relevance score exceeds the threshold
    """
    # If we already have a stored relevance score, use it
    if 'relevance_score' in story and story['relevance_score'] is not None:
        return story['relevance_score'] >= threshold
    
    # Otherwise, calculate a new score
    score = get_relevance_score(story)
    
    # Store the score in the story dictionary for potential later use
    story['relevance_score'] = score
    
    return score >= threshold

@lru_cache(maxsize=128)
def get_domain_relevance_score(domain: str) -> int:
    """Calculate a relevance score for a domain, with caching.
    
    This function is used as an optimization for domains that
    regularly appear in HN stories.
    
    Args:
        domain (str): The website domain
        
    Returns:
        int: Relevance score from 0-100
    """
    # Simple domain-based prompt
    prompt = f"Domain: {domain}"
    
    # Use the same system prompt as the main function
    system_prompt = """Evaluate how strongly this website domain would match the following interest categories:

1. Technology & Tools:
   - Emacs, Linux, NixOS, MacOS, Apple hardware
   - E-book readers and related technology

2. Programming & Computer Science:
   - Python, Julia, Lisp
   - Functional programming, logic programming
   - Any interesting programming language concepts

3. Security & Hacking:
   - Infosec, cybersecurity, penetration testing
   - Ethical hacking, cracking (in educational context)
   - Security research, vulnerabilities

4. Projects & Creativity:
   - DIY/home projects with technology
   - Creative coding, generative art
   - Hardware hacking, electronics

5. Science & Research:
   - AI, machine learning, LLMs
   - Climate change, environmental tech
   - Scientific computing

6. Books & Reading:
   - Technical books, programming books
   - E-book technology, digital reading

Rate the domain's relevance to these interests on a scale from 0-100, where:
- 0-25: Not relevant to these interests
- 26-50: Slightly relevant to these interests
- 51-75: Moderately relevant to these interests
- 76-100: Highly relevant to these interests

ONLY respond with a single integer between 0 and 100, and nothing else."""
    
    try:
        message = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=100,
            temperature=0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        response = message.content[0].text.strip()
        try:
            score = int(response)
            return max(0, min(100, score))
        except ValueError:
            return 0
    except Exception:
        return 0

async def get_relevance_score_async(story: Dict[str, Any]) -> int:
    """Asynchronous version of get_relevance_score.
    
    Args:
        story (Dict[str, Any]): Story details from the Hacker News API
        
    Returns:
        int: Relevance score from 0-100
    """
    title = story.get('title', '')
    url = story.get('url', '')
    
    # Extract domain if URL is available
    domain = ""
    if url and '://' in url:
        domain = url.split('://')[1].split('/')[0]
        
        # Check if we already have a cached score for this domain
        # If the domain has been seen before, we can use a simplified approach
        if domain:
            try:
                # Use the cached function
                domain_score = get_domain_relevance_score(domain)
                # If the domain has a low score, we can trust it more than if it has a high score
                # (High scoring domains might have irrelevant articles)
                if domain_score < 30:
                    return domain_score
            except Exception:
                # Fall back to full analysis if there's an error
                pass
    
    # Construct prompt with all available information
    prompt = f"Title: {title}\nDomain: {domain}\nURL: {url}"
    
    # Interest categories defined in the system prompt
    system_prompt = """Evaluate how strongly this Hacker News story would match the following interest categories:

1. Technology & Tools:
   - Emacs, Linux, NixOS, MacOS, Apple hardware
   - E-book readers and related technology

2. Programming & Computer Science:
   - Python, Julia, Lisp
   - Functional programming, logic programming
   - Any interesting programming language concepts

3. Security & Hacking:
   - Infosec, cybersecurity, penetration testing
   - Ethical hacking, cracking (in educational context)
   - Security research, vulnerabilities

4. Projects & Creativity:
   - DIY/home projects with technology
   - Creative coding, generative art
   - Hardware hacking, electronics

5. Science & Research:
   - AI, machine learning, LLMs
   - Climate change, environmental tech
   - Scientific computing

6. Books & Reading:
   - Technical books, programming books
   - E-book technology, digital reading

Rate the story's relevance to these interests on a scale from 0-100, where:
- 0-25: Not relevant to these interests
- 26-50: Slightly relevant to these interests
- 51-75: Moderately relevant to these interests
- 76-100: Highly relevant to these interests

ONLY respond with a single integer between 0 and 100, and nothing else."""
    
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
        # Log error and default to 0
        print(f"Error calculating relevance score asynchronously: {e}")
        return 0

async def process_story_batch_async(stories: List[Dict[str, Any]], throttle_delay: float = 0.2) -> List[Dict[str, Any]]:
    """Process a batch of stories asynchronously to get relevance scores.
    
    Args:
        stories (List[Dict[str, Any]]): List of story dictionaries to process
        throttle_delay (float): Delay between API calls to avoid rate limits
        
    Returns:
        List[Dict[str, Any]]: List of stories with added relevance scores
    """
    tasks = []
    
    for i, story in enumerate(stories):
        # Add throttling delay to avoid hitting rate limits
        # Space out the calls slightly for better API behavior
        await asyncio.sleep(throttle_delay * i)
        task = asyncio.create_task(get_relevance_score_async(story))
        tasks.append((story, task))
    
    # Wait for all tasks to complete and update stories
    for story, task in tasks:
        try:
            story['relevance_score'] = await task
        except Exception as e:
            print(f"Error processing story {story.get('id')}: {e}")
            story['relevance_score'] = 0
    
    return stories
