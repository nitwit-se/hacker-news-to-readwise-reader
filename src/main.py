#!/usr/bin/env python3

import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_last_poll_time, update_last_poll_time, save_stories, get_story_ids_since
from src.db import update_story_content, get_stories_needing_content, get_story_with_content
from src.api import get_new_stories, get_stories_details
from src.content import process_story_batch

def format_story(story):
    """Format a story for console output.
    
    Args:
        story (dict): Story details
        
    Returns:
        str: Formatted story string
    """
    title = story.get('title', 'No title')
    url = story.get('url', '')
    score = story.get('score', 0)
    author = story.get('by', 'unknown')
    story_id = story.get('id', 'unknown')
    content_fetched = story.get('content_fetched', 0)
    
    # Format the timestamp
    timestamp = datetime.fromtimestamp(story.get('time', 0))
    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    # Create the output string
    output = f"\n{title}\n"
    output += f"ID: {story_id} | Score: {score} | By: {author} | Posted: {time_str}\n"
    
    if url:
        output += f"URL: {url}\n"
    else:
        # If no URL, it's probably an Ask HN post
        output += f"URL: https://news.ycombinator.com/item?id={story['id']}\n"
    
    # Check if it's a Twitter/X URL (more precisely)
    is_twitter_url = False
    if url:
        from urllib.parse import urlparse
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Check against exact domains
        twitter_domains = ['twitter.com', 'x.com', 't.co']
        if domain in twitter_domains:
            is_twitter_url = True
    
    # Add content summary if available
    if story.get('content_summary'):
        output += f"\nSummary: {story['content_summary']}\n"
    elif is_twitter_url or content_fetched == 3:
        output += "\nSummary: [Twitter/X content not available - view directly on Twitter]\n"
    elif story.get('error_type'):
        error_type = story.get('error_type')
        error_msg = story.get('error_message', '')
        output += f"\nSummary: [Content unavailable: {error_type}] {error_msg}\n"
    
    return output

def fetch_story_content(stories, content_limit=5, retry_failed=False):
    """Fetch content for stories that have URLs but no content yet.
    
    Args:
        stories (list): List of story dictionaries
        content_limit (int): Maximum number of stories to fetch content for
        retry_failed (bool): Whether to retry stories that previously failed
        
    Returns:
        list: List of stories with content added
    """
    # Get story IDs from the provided stories list
    story_ids = [story['id'] for story in stories]
    
    # First check if we need to prioritize specific stories
    if story_ids:
        # Only fetch content for the stories provided in the list, up to content_limit
        # This allows us to prioritize fetching content for new stories
        stories_to_fetch = []
        
        # Sort the stories list to prioritize stories without content
        for story in stories:
            # Only consider stories with URLs
            if story.get('url'):
                # Check if the story already has content
                full_story = get_story_with_content(story['id'])
                if full_story and not full_story.get('content'):
                    # Story has a URL but no content, add it to the list
                    stories_to_fetch.append({
                        'id': story['id'],
                        'url': story['url']
                    })
                    
                    if len(stories_to_fetch) >= content_limit:
                        break
    else:
        # If no specific stories provided, fetch content for any stories in the database
        stories_to_fetch = get_stories_needing_content(
            limit=content_limit, 
            retry_failed=retry_failed
        )
    
    if not stories_to_fetch:
        return stories
    
    print(f"Fetching content for {len(stories_to_fetch)} stories...")
    
    # Process stories to get content
    processed_stories = process_story_batch(stories_to_fetch)
    
    # Update the database with the fetched content or error information
    for story in processed_stories:
        if story.get('content') and story.get('content_fetched') == 1:
            # Successful content fetch
            update_story_content(story['id'], content=story['content'])
            print(f"Updated content for story ID {story['id']}")
        else:
            # Failed content fetch
            error_info = {
                'error_type': story.get('error_type', 'Unknown'),
                'error_message': story.get('error_message', 'Unknown error'),
                'error_status': story.get('error_status')
            }
            update_story_content(story['id'], error_info=error_info)
            print(f"Recorded error for story ID {story['id']}: {error_info['error_type']}")
    
    # Add content summaries to the story list for display
    story_map = {story['id']: story for story in processed_stories}
    
    for story in stories:
        if story['id'] in story_map:
            story['content_summary'] = story_map[story['id']].get('content_summary', '')
            
            # Also add error information if available
            if not story.get('content_summary') and story_map[story['id']].get('error_type'):
                error_type = story_map[story['id']].get('error_type')
                error_msg = story_map[story['id']].get('error_message', '')
                story['content_summary'] = f"[Content Error: {error_type}] {error_msg}"
    
    return stories

def poll_hacker_news(limit=30, content_limit=5, retry_failed=False):
    """Poll Hacker News for new stories.
    
    Args:
        limit (int): Maximum number of stories to retrieve
        content_limit (int): Maximum number of stories to fetch content for
        retry_failed (bool): Whether to retry stories that previously failed
        
    Returns:
        list: List of new stories
    """
    # Initialize database if not exists
    init_db()
    
    # Get the timestamp of the last poll
    last_poll_time = get_last_poll_time()
    print(f"Last poll time: {last_poll_time}\n")
    
    # Get new story IDs from the API
    new_story_ids = get_new_stories(limit=limit)
    print(f"Fetched {len(new_story_ids)} story IDs from Hacker News API\n")
    
    # Get details for each story
    stories = get_stories_details(new_story_ids)
    print(f"Retrieved details for {len(stories)} stories\n")
    
    # Save stories to the database
    new_count = save_stories(stories)
    
    # Get IDs of stories added since the last poll (before updating last_poll_time)
    new_story_ids = get_story_ids_since(last_poll_time)
    
    # Fetch content for all new stories first (priority), then for others if limit allows
    if new_story_ids and content_limit > 0:
        # Create a list of just the new stories
        new_stories_raw = [story for story in stories if story['id'] in new_story_ids]
        
        # Calculate how many slots we have for non-new stories
        remaining_limit = max(0, content_limit - len(new_stories_raw))
        
        # First fetch content for new stories
        if new_stories_raw:
            print(f"Fetching content for new stories first...")
            fetch_story_content(
                new_stories_raw,
                content_limit=min(len(new_stories_raw), content_limit),
                retry_failed=retry_failed
            )
        
        # Then fetch content for other stories if we have remaining slots
        if remaining_limit > 0:
            other_stories = [story for story in stories if story['id'] not in new_story_ids]
            if other_stories:
                print(f"Fetching content for {remaining_limit} additional stories...")
                fetch_story_content(
                    other_stories,
                    content_limit=remaining_limit,
                    retry_failed=retry_failed
                )
    else:
        # Original behavior if no new stories or content_limit is 0
        stories = fetch_story_content(
            stories, 
            content_limit=content_limit,
            retry_failed=retry_failed
        )
    
    # Update the last poll time
    update_last_poll_time()
    
    # Get full story details with content for each new story
    new_stories = []
    for story_id in new_story_ids:
        # Try to get the full story with content from database
        full_story = get_story_with_content(story_id)
        if full_story:
            new_stories.append(full_story)
    
    return new_stories

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description='Poll Hacker News for new stories')
    parser.add_argument('--limit', type=int, default=30,
                        help='Maximum number of stories to retrieve')
    parser.add_argument('--content-limit', type=int, default=5,
                        help='Maximum number of stories to fetch content for')
    parser.add_argument('--skip-content', action='store_true',
                        help='Skip fetching content for stories')
    parser.add_argument('--retry-failed', action='store_true',
                        help='Retry fetching content for stories that previously failed')
    args = parser.parse_args()
    
    print(f"Polling Hacker News for new stories (limit: {args.limit})...\n")
    
    try:
        # Set content_limit to 0 if skip_content is True
        content_limit = 0 if args.skip_content else args.content_limit
        
        new_stories = poll_hacker_news(
            limit=args.limit, 
            content_limit=content_limit, 
            retry_failed=args.retry_failed
        )
        
        if new_stories:
            print(f"Found {len(new_stories)} new stories since last poll:")
            for story in sorted(new_stories, key=lambda x: x.get('score', 0), reverse=True):
                print(format_story(story))
        else:
            print("No new stories found since last poll.")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())