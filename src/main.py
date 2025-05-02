#!/usr/bin/env python3

import sys
import os
import argparse
import asyncio
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_last_poll_time, update_last_poll_time
from src.db import get_last_oldest_id, update_last_oldest_id
from src.db import save_or_update_stories, get_stories_within_timeframe
from src.api import get_stories_until_cutoff, get_stories_details_async

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
    
    return output

async def poll_hacker_news_async(hours=24, min_score=10, batch_size=100, max_batches=10):
    """Poll Hacker News for stories from the past 24 hours with score >= min_score.
    
    Args:
        hours (int): Number of hours to look back
        min_score (int): Minimum score threshold for displaying stories
        batch_size (int): Size of each batch of stories to process
        max_batches (int): Maximum number of batches to process
        
    Returns:
        list: List of stories meeting the criteria
    """
    # Initialize database if not exists
    init_db()
    
    # Get the timestamp of the last poll and the last oldest ID
    last_poll_time = get_last_poll_time()
    last_oldest_id = get_last_oldest_id()
    
    print(f"Last poll time: {last_poll_time}")
    print(f"Last oldest story ID: {last_oldest_id or 'None'}\n")
    
    # Get new stories and oldest ID processed in this run
    print(f"Fetching stories from the past {hours} hours...")
    stories, oldest_id = get_stories_until_cutoff(
        last_oldest_id=last_oldest_id,
        hours=hours,
        batch_size=batch_size,
        max_batches=max_batches
    )
    
    print(f"Found {len(stories)} stories within the {hours}-hour timeframe\n")
    
    # Update the last oldest ID for the next run
    if oldest_id:
        update_last_oldest_id(oldest_id)
        print(f"Updated last oldest story ID to: {oldest_id}\n")
    
    # Save new stories and update existing ones
    new_count, update_count = save_or_update_stories(stories)
    print(f"Added {new_count} new stories and updated {update_count} existing stories\n")
    
    # Update the last poll time
    update_last_poll_time()
    
    # Get all stories from the past 24 hours with score >= min_score
    high_score_stories = get_stories_within_timeframe(hours=hours, min_score=min_score)
    print(f"Found {len(high_score_stories)} stories with score >= {min_score} from the past {hours} hours\n")
    
    return high_score_stories

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description='Poll Hacker News for recent high-quality stories')
    parser.add_argument('--hours', type=int, default=24,
                        help='Number of hours to look back')
    parser.add_argument('--min-score', type=int, default=10,
                        help='Minimum score threshold for displaying stories')
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Size of each batch of stories to process')
    parser.add_argument('--max-batches', type=int, default=10,
                        help='Maximum number of batches to process')
    args = parser.parse_args()
    
    print(f"Polling Hacker News for stories from the past {args.hours} hours with score >= {args.min_score}...\n")
    
    try:
        # Run the async function in the event loop
        high_score_stories = asyncio.run(poll_hacker_news_async(
            hours=args.hours,
            min_score=args.min_score,
            batch_size=args.batch_size,
            max_batches=args.max_batches
        ))
        
        if high_score_stories:
            print(f"Top stories from the past {args.hours} hours (score >= {args.min_score}):")
            for story in high_score_stories:
                print(format_story(story))
        else:
            print(f"No stories with score >= {args.min_score} found from the past {args.hours} hours.")
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())