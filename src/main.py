#!/usr/bin/env python3

import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_last_poll_time, update_last_poll_time, save_stories, get_story_ids_since
from src.api import get_new_stories, get_stories_details

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
    
    # Format the timestamp
    timestamp = datetime.fromtimestamp(story.get('time', 0))
    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
    # Create the output string
    output = f"\n{title}\n"
    output += f"Score: {score} | By: {author} | Posted: {time_str}\n"
    
    if url:
        output += f"URL: {url}\n"
    else:
        # If no URL, it's probably an Ask HN post
        output += f"URL: https://news.ycombinator.com/item?id={story['id']}\n"
    
    return output

def poll_hacker_news(limit=30):
    """Poll Hacker News for new stories.
    
    Args:
        limit (int): Maximum number of stories to retrieve
        
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
    
    # Update the last poll time
    update_last_poll_time()
    
    # Get IDs of stories added since the last poll
    new_story_ids = get_story_ids_since(last_poll_time)
    
    # Filter stories to include only those added since the last poll
    new_stories = [story for story in stories if story['id'] in new_story_ids]
    
    return new_stories

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description='Poll Hacker News for new stories')
    parser.add_argument('--limit', type=int, default=30,
                        help='Maximum number of stories to retrieve')
    args = parser.parse_args()
    
    print(f"Polling Hacker News for new stories (limit: {args.limit})...\n")
    
    try:
        new_stories = poll_hacker_news(limit=args.limit)
        
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