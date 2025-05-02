import requests
import time

# Hacker News API base URL
API_BASE_URL = 'https://hacker-news.firebaseio.com/v0/'

def get_top_stories(limit=100):
    """Get IDs of current top stories.
    
    Args:
        limit (int): Maximum number of stories to fetch
        
    Returns:
        list: List of story IDs
    """
    url = f"{API_BASE_URL}topstories.json"
    response = requests.get(url)
    response.raise_for_status()
    
    # Return only the requested number of stories
    return response.json()[:limit]

def get_new_stories(limit=100):
    """Get IDs of newest stories.
    
    Args:
        limit (int): Maximum number of stories to fetch
        
    Returns:
        list: List of story IDs
    """
    url = f"{API_BASE_URL}newstories.json"
    response = requests.get(url)
    response.raise_for_status()
    
    # Return only the requested number of stories
    return response.json()[:limit]

def get_story(story_id):
    """Get details for a specific story by ID.
    
    Args:
        story_id (int): The story ID to fetch
        
    Returns:
        dict: Story details or None if not found
    """
    url = f"{API_BASE_URL}item/{story_id}.json"
    response = requests.get(url)
    
    if response.status_code == 404:
        return None
        
    response.raise_for_status()
    return response.json()

def get_stories_details(story_ids, delay=0.05):
    """Get details for multiple stories.
    
    Args:
        story_ids (list): List of story IDs to fetch
        delay (float): Delay between requests to avoid rate limiting
        
    Returns:
        list: List of story detail dictionaries
    """
    stories = []
    
    for story_id in story_ids:
        story = get_story(story_id)
        if story and story.get('type') == 'story':
            stories.append(story)
        
        # Add a small delay to avoid hammering the API
        time.sleep(delay)
    
    return stories