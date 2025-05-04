import requests
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional, Any, Union, cast

# Hacker News API base URL
API_BASE_URL = 'https://hacker-news.firebaseio.com/v0/'

def get_best_stories(limit: int = 500) -> List[int]:
    """Get IDs of best stories.
    
    Args:
        limit (int): Maximum number of stories to fetch
        
    Returns:
        List[int]: List of story IDs
    """
    url = f"{API_BASE_URL}beststories.json"
    response = requests.get(url)
    response.raise_for_status()
    
    # Return only the requested number of stories
    return response.json()[:limit]

def get_top_stories(limit: int = 500) -> List[int]:
    """Get IDs of current top stories.
    
    Args:
        limit (int): Maximum number of stories to fetch
        
    Returns:
        List[int]: List of story IDs
    """
    url = f"{API_BASE_URL}topstories.json"
    response = requests.get(url)
    response.raise_for_status()
    
    # Return only the requested number of stories
    return response.json()[:limit]

def get_new_stories(limit: int = 500) -> List[int]:
    """Get IDs of newest stories.
    
    Args:
        limit (int): Maximum number of stories to fetch
        
    Returns:
        List[int]: List of story IDs
    """
    url = f"{API_BASE_URL}newstories.json"
    response = requests.get(url)
    response.raise_for_status()
    
    # Return only the requested number of stories
    return response.json()[:limit]

def get_story(story_id: int) -> Optional[Dict[str, Any]]:
    """Get details for a specific story by ID.
    
    Args:
        story_id (int): The story ID to fetch
        
    Returns:
        Optional[Dict[str, Any]]: Story details or None if not found
    """
    url = f"{API_BASE_URL}item/{story_id}.json"
    response = requests.get(url)
    
    if response.status_code == 404:
        return None
        
    response.raise_for_status()
    return response.json()

def get_stories_details(story_ids: List[int], delay: float = 0.05) -> List[Dict[str, Any]]:
    """Get details for multiple stories.
    
    Args:
        story_ids (List[int]): List of story IDs to fetch
        delay (float): Delay between requests to avoid rate limiting
        
    Returns:
        List[Dict[str, Any]]: List of story detail dictionaries
    """
    stories: List[Dict[str, Any]] = []
    
    for story_id in story_ids:
        story = get_story(story_id)
        if story and story.get('type') == 'story':
            stories.append(story)
        
        # Add a small delay to avoid hammering the API
        time.sleep(delay)
    
    return stories

def get_stories_batch(start_index: int = 0, batch_size: int = 100) -> List[int]:
    """Get a batch of newest stories from the specified starting index.
    
    Args:
        start_index (int): Starting index for the batch
        batch_size (int): Number of stories to fetch in this batch
        
    Returns:
        List[int]: List of story IDs in this batch
    """
    all_new_story_ids = get_new_stories(500)  # Get a large enough list to handle batching
    
    # Handle out-of-range indices
    if start_index >= len(all_new_story_ids):
        return []
    
    end_index = min(start_index + batch_size, len(all_new_story_ids))
    return all_new_story_ids[start_index:end_index]

def is_story_within_timeframe(story: Optional[Dict[str, Any]], hours: int = 24) -> bool:
    """Check if a story is within the specified timeframe.
    
    Args:
        story (Optional[Dict[str, Any]]): Story details dictionary
        hours (int): Number of hours to look back
        
    Returns:
        bool: True if the story is within timeframe, False otherwise
    """
    if not story or 'time' not in story:
        return False
    
    # The story['time'] is a Unix timestamp in seconds (UTC)
    # Convert it to UTC datetime for consistent timezone handling
    story_time = datetime.fromtimestamp(story['time'], tz=timezone.utc)
    
    # Use UTC for the cutoff time as well
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    return story_time >= cutoff_time

async def get_story_async(session: aiohttp.ClientSession, story_id: int) -> Optional[Dict[str, Any]]:
    """Get details for a specific story by ID asynchronously.
    
    Args:
        session (aiohttp.ClientSession): Async HTTP session
        story_id (int): The story ID to fetch
        
    Returns:
        Optional[Dict[str, Any]]: Story details or None if not found
    """
    url = f"{API_BASE_URL}item/{story_id}.json"
    
    try:
        async with session.get(url) as response:
            if response.status == 404:
                return None
            
            response.raise_for_status()
            return await response.json()
    except Exception:
        return None

async def get_stories_details_async(story_ids: List[int], concurrency: int = 10) -> List[Dict[str, Any]]:
    """Get details for multiple stories asynchronously.
    
    Args:
        story_ids (List[int]): List of story IDs to fetch
        concurrency (int): Maximum number of concurrent requests
        
    Returns:
        List[Dict[str, Any]]: List of story detail dictionaries
    """
    stories: List[Dict[str, Any]] = []
    semaphore = asyncio.Semaphore(concurrency)
    
    async with aiohttp.ClientSession() as session:
        async def fetch_with_semaphore(story_id: int) -> Optional[Dict[str, Any]]:
            async with semaphore:
                story = await get_story_async(session, story_id)
                if story and story.get('type') == 'story':
                    return story
                return None
        
        tasks = [fetch_with_semaphore(story_id) for story_id in story_ids]
        results = await asyncio.gather(*tasks)
        
        # Filter out None values
        stories = [story for story in results if story]
    
    return stories

def get_max_item_id() -> int:
    """Get the current maximum item ID from Hacker News.
    
    Returns:
        int: The maximum item ID
    """
    url = f"{API_BASE_URL}maxitem.json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_stories_from_maxitem(hours: int = 24, batch_size: int = 100, max_batches: int = 10, consecutive_old_threshold: int = 5) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Get all recent stories by working backwards from the maximum item ID.
    
    This function fetches stories in batches, starting from the most recent item
    and working backwards. It continues until it finds a certain number of consecutive
    items older than the specified timeframe.
    
    Args:
        hours (int): Number of hours to look back
        batch_size (int): Size of each batch of stories to process
        max_batches (int): Maximum number of batches to process
        consecutive_old_threshold (int): Number of consecutive old items to find before stopping
        
    Returns:
        Tuple[List[Dict[str, Any]], Optional[int]]: (all_stories, oldest_id) - List of stories within timeframe and oldest ID processed
    """
    all_stories: List[Dict[str, Any]] = []
    oldest_id: Optional[int] = None
    consecutive_old_count = 0
    
    # Get the current maximum item ID
    max_item_id = get_max_item_id()
    current_id = max_item_id
    
    # Process stories in batches
    for batch_num in range(max_batches):
        # Generate a batch of IDs going backwards from current_id
        batch_ids = list(range(current_id, current_id - batch_size, -1))
        current_id -= batch_size
        
        # If we have no more IDs to process or reached ID 1, we're done
        if not batch_ids or batch_ids[-1] <= 1:
            break
        
        # Get details for this batch
        batch_stories = get_stories_details(batch_ids)
        
        # Track if we found any stories within timeframe in this batch
        found_recent = False
        
        # Process each story
        for story in batch_stories:
            if not story:
                continue
                
            # Set the oldest ID we've seen (for tracking)
            if oldest_id is None or story['id'] < oldest_id:
                oldest_id = story['id']
                
            # Check if this story is within our timeframe
            if is_story_within_timeframe(story, hours):
                all_stories.append(story)
                consecutive_old_count = 0  # Reset consecutive old count
                found_recent = True
            else:
                # We've found a story outside our timeframe
                consecutive_old_count += 1
        
        # If we haven't found any recent stories in this batch, increment the counter
        if not found_recent:
            consecutive_old_count += 1
        
        # If we've found enough consecutive old items, we can stop
        if consecutive_old_count >= consecutive_old_threshold:
            break
    
    return all_stories, oldest_id

def get_stories_until_cutoff(last_oldest_id: Optional[int] = None, hours: int = 24, batch_size: int = 100, max_batches: int = 10) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Get all new stories until reaching the 24-hour cutoff or last known ID.
    
    This function fetches stories in batches until it either:
    1. Finds a story older than the cutoff time
    2. Reaches the last_oldest_id from a previous run
    3. Processes the maximum number of allowed batches
    
    Args:
        last_oldest_id (Optional[int]): The ID of the oldest story from the previous run
        hours (int): Number of hours to look back
        batch_size (int): Size of each batch of stories to process
        max_batches (int): Maximum number of batches to process
        
    Returns:
        Tuple[List[Dict[str, Any]], Optional[int]]: (all_stories, oldest_id) - List of stories within timeframe and oldest ID processed
    """
    all_stories: List[Dict[str, Any]] = []
    oldest_id: Optional[int] = None
    reached_cutoff = False
    
    # Get all new story IDs
    all_new_story_ids = get_new_stories(500)
    
    # Process stories in batches
    for batch_num in range(max_batches):
        start_idx = batch_num * batch_size
        if start_idx >= len(all_new_story_ids):
            break
            
        end_idx = min(start_idx + batch_size, len(all_new_story_ids))
        batch_ids = all_new_story_ids[start_idx:end_idx]
        
        # If we have no more IDs to process, we're done
        if not batch_ids:
            break
            
        # If we reached the last_oldest_id from previous run, we can stop
        if last_oldest_id and last_oldest_id in batch_ids:
            oldest_id = last_oldest_id
            idx = batch_ids.index(last_oldest_id)
            # Only process stories newer than the last_oldest_id
            batch_ids = batch_ids[:idx]
            if not batch_ids:
                break
        
        # Get details for this batch
        batch_stories = get_stories_details(batch_ids)
        
        # Process each story
        for story in batch_stories:
            if not story:
                continue
                
            # Set the oldest ID we've seen (for the next run)
            if oldest_id is None or story['id'] < oldest_id:
                oldest_id = story['id']
                
            # Check if this story is within our timeframe
            if is_story_within_timeframe(story, hours):
                all_stories.append(story)
            else:
                # We've reached a story outside our timeframe
                reached_cutoff = True
        
        # If we've reached the cutoff, we can stop processing more batches
        if reached_cutoff:
            break
    
    return all_stories, oldest_id


async def get_filtered_stories_async(source: str = 'top', hours: int = 24, min_score: int = 10, limit: int = 500) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Get high-quality stories efficiently using the specified source.
    
    This optimized function:
    1. Fetches IDs for top, best, or new stories in bulk
    2. Gets story details asynchronously with higher concurrency
    3. Filters by time and score
    
    Args:
        source (str): Where to get stories from - 'top', 'best', or 'new'
        hours (int): Number of hours to look back
        min_score (int): Minimum score for a story to be included
        limit (int): Maximum number of stories to process
        
    Returns:
        Tuple[List[Dict[str, Any]], Optional[int]]: (stories, oldest_id) - List of filtered stories and oldest ID processed
    """
    # Get story IDs from the selected source
    if source == 'top':
        story_ids = get_top_stories(limit)
    elif source == 'best':
        story_ids = get_best_stories(limit)
    else:  # default to 'new'
        story_ids = get_new_stories(limit)
    
    # Get story details asynchronously
    all_stories = await get_stories_details_async(story_ids)
    
    # Filter by time and score
    filtered_stories: List[Dict[str, Any]] = []
    oldest_id: Optional[int] = None
    
    for story in all_stories:
        # Track oldest ID for future reference
        if oldest_id is None or story['id'] < oldest_id:
            oldest_id = story['id']
            
        # Filter by time and score
        if is_story_within_timeframe(story, hours) and story.get('score', 0) >= min_score:
            filtered_stories.append(story)
    
    # Sort by score (highest first)
    filtered_stories.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    return filtered_stories, oldest_id