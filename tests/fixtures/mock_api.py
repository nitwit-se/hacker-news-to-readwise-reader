"""
API mocking utilities for testing.
"""

import json
import re
from typing import Dict, Any, List, Union, Optional, Pattern, Callable
import responses
from aioresponses import aioresponses
from .api_responses import (
    TOP_STORIES_RESPONSE,
    BEST_STORIES_RESPONSE, 
    NEW_STORIES_RESPONSE,
    MAX_ITEM_RESPONSE,
    STORY_RESPONSES,
    get_mock_story_response
)

# Hacker News API base URL
API_BASE_URL = 'https://hacker-news.firebaseio.com/v0/'

# Regex patterns for API endpoints
TOPSTORIES_PATTERN = re.compile(r'https://hacker-news\.firebaseio\.com/v0/topstories\.json.*')
BESTSTORIES_PATTERN = re.compile(r'https://hacker-news\.firebaseio\.com/v0/beststories\.json.*')
NEWSTORIES_PATTERN = re.compile(r'https://hacker-news\.firebaseio\.com/v0/newstories\.json.*')
MAXITEM_PATTERN = re.compile(r'https://hacker-news\.firebaseio\.com/v0/maxitem\.json.*')
ITEM_PATTERN = re.compile(r'https://hacker-news\.firebaseio\.com/v0/item/(\d+)\.json.*')


def mock_hn_api(mock_responses: responses.RequestsMock) -> None:
    """
    Set up mock responses for the Hacker News API.
    
    Args:
        mock_responses: The responses.RequestsMock instance to add mocks to
    """
    # Mock topstories endpoint
    mock_responses.add(
        responses.GET,
        TOPSTORIES_PATTERN,
        json=TOP_STORIES_RESPONSE,
        status=200
    )
    
    # Mock beststories endpoint
    mock_responses.add(
        responses.GET,
        BESTSTORIES_PATTERN,
        json=BEST_STORIES_RESPONSE,
        status=200
    )
    
    # Mock newstories endpoint
    mock_responses.add(
        responses.GET,
        NEWSTORIES_PATTERN,
        json=NEW_STORIES_RESPONSE,
        status=200
    )
    
    # Mock maxitem endpoint
    mock_responses.add(
        responses.GET,
        MAXITEM_PATTERN,
        json=MAX_ITEM_RESPONSE,
        status=200
    )
    
    # Mock item endpoints with callback
    mock_responses.add_callback(
        responses.GET,
        ITEM_PATTERN,
        callback=_item_callback,
        content_type='application/json',
    )


def _item_callback(request) -> tuple[int, Dict[str, str], Union[str, bytes]]:
    """
    Callback for handling item requests based on the ID in the URL.
    """
    match = ITEM_PATTERN.match(request.url)
    if match:
        item_id = int(match.group(1))
        story = STORY_RESPONSES.get(item_id)
        
        # If we have a specific response for this ID, use it
        if story is not None:
            if story:  # Not None but an actual dictionary
                return 200, {'Content-Type': 'application/json'}, json.dumps(story)
            else:
                return 404, {'Content-Type': 'application/json'}, json.dumps(None)
                
        # Otherwise generate a generic response
        return 200, {'Content-Type': 'application/json'}, json.dumps(get_mock_story_response(item_id))
    
    # Fallback for any unmatched URLs
    return 404, {'Content-Type': 'application/json'}, json.dumps(None)


def mock_hn_api_async(mock_aioresponses: aioresponses) -> None:
    """
    Set up mock responses for the async Hacker News API.
    
    Args:
        mock_aioresponses: The aioresponses instance to add mocks to
    """
    # Mock topstories endpoint
    mock_aioresponses.get(
        f"{API_BASE_URL}topstories.json",
        status=200,
        payload=TOP_STORIES_RESPONSE
    )
    
    # Mock beststories endpoint
    mock_aioresponses.get(
        f"{API_BASE_URL}beststories.json",
        status=200,
        payload=BEST_STORIES_RESPONSE
    )
    
    # Mock newstories endpoint
    mock_aioresponses.get(
        f"{API_BASE_URL}newstories.json",
        status=200,
        payload=NEW_STORIES_RESPONSE
    )
    
    # Mock maxitem endpoint
    mock_aioresponses.get(
        f"{API_BASE_URL}maxitem.json",
        status=200,
        payload=MAX_ITEM_RESPONSE
    )
    
    # Add specific story responses
    for story_id, story_data in STORY_RESPONSES.items():
        if story_data is not None:  # For 'found' stories
            mock_aioresponses.get(
                f"{API_BASE_URL}item/{story_id}.json",
                status=200,
                payload=story_data
            )
        else:  # For 'not found' stories
            mock_aioresponses.get(
                f"{API_BASE_URL}item/{story_id}.json",
                status=404,
                payload=None
            )
    
    # Generate responses for the test story IDs that we know we'll need
    for i in range(10):
        story_id = 39428394 + i
        if story_id not in STORY_RESPONSES:
            mock_aioresponses.get(
                f"{API_BASE_URL}item/{story_id}.json",
                status=200,
                payload=get_mock_story_response(story_id)
            )
    
    # Add responses for TOP_STORIES_RESPONSE IDs
    for story_id in TOP_STORIES_RESPONSE[:20]:  # Just do the first 20 to keep it reasonable
        if story_id not in STORY_RESPONSES:
            mock_aioresponses.get(
                f"{API_BASE_URL}item/{story_id}.json",
                status=200,
                payload=get_mock_story_response(story_id)
            )
            
    # Add responses for BEST_STORIES_RESPONSE IDs
    for story_id in BEST_STORIES_RESPONSE[:20]:  # Just do the first 20
        if story_id not in STORY_RESPONSES:
            mock_aioresponses.get(
                f"{API_BASE_URL}item/{story_id}.json",
                status=200,
                payload=get_mock_story_response(story_id)
            )
            
    # Add responses for NEW_STORIES_RESPONSE IDs
    for story_id in NEW_STORIES_RESPONSE[:20]:  # Just do the first 20
        if story_id not in STORY_RESPONSES:
            mock_aioresponses.get(
                f"{API_BASE_URL}item/{story_id}.json",
                status=200,
                payload=get_mock_story_response(story_id)
            )
    
    # Add a pattern matcher for any other story IDs
    url_pattern = re.compile(r'https://hacker-news\.firebaseio\.com/v0/item/(\d+)\.json.*')
    
    def _get_generic_story(url, **kwargs):
        match = url_pattern.match(url)
        if match:
            story_id = int(match.group(1))
            # Skip if we already have a specific response for this ID
            if story_id not in STORY_RESPONSES:
                return {
                    'status': 200,
                    'payload': get_mock_story_response(story_id)
                }
        return None
    
    mock_aioresponses.get(
        url_pattern,
        callback=_get_generic_story
    )