#!/usr/bin/env python3

import sys
import os
import argparse
import asyncio
import time
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_last_poll_time, update_last_poll_time
from src.db import get_last_oldest_id, update_last_oldest_id
from src.db import save_or_update_stories, get_stories_within_timeframe, update_story_scores
from src.db import get_unscored_stories_in_batches
from src.api import get_stories_until_cutoff, get_stories_details_async, get_stories_from_maxitem
from src.api import get_filtered_stories_async
from src.classifier import is_interesting, get_relevance_score
from src.classifier import process_story_batch_async, get_relevance_score_async

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
    
    # Include relevance score if available
    relevance_info = ""
    if 'relevance_score' in story and story['relevance_score'] is not None:
        relevance_info = f" | Relevance: {story['relevance_score']}"
    
    output += f"ID: {story_id} | Score: {score}{relevance_info} | By: {author} | Posted: {time_str}\n"
    
    if url:
        output += f"URL: {url}\n"
    else:
        # If no URL, it's probably an Ask HN post
        output += f"URL: https://news.ycombinator.com/item?id={story['id']}\n"
    
    return output

async def poll_hacker_news_async(hours=24, min_score=30, source='top', limit=500, min_relevance=None):
    """Poll Hacker News for high-quality stories using an optimized approach.
    
    Args:
        hours (int): Number of hours to look back
        min_score (int): Minimum score threshold for displaying stories
        source (str): Source to use - 'top', 'best', or 'new'
        limit (int): Maximum number of stories to fetch from source
        min_relevance (int, optional): Minimum relevance score threshold
        
    Returns:
        list: List of stories meeting the criteria
    """
    # Initialize database if not exists
    init_db()
    
    # Get the timestamp of the last poll
    last_poll_time = get_last_poll_time()
    print(f"Last poll time: {last_poll_time}\n")
    
    # Get filtered stories efficiently using the specified source
    print(f"Fetching {source} stories from the past {hours} hours with score >= {min_score}...")
    start_time = datetime.now()
    
    # Use our optimized function to get high-quality stories in one go
    stories, oldest_id = await get_filtered_stories_async(
        source=source,
        hours=hours,
        min_score=min_score,
        limit=limit
    )
    
    elapsed_time = (datetime.now() - start_time).total_seconds()
    print(f"Found {len(stories)} stories in {elapsed_time:.2f} seconds\n")
    
    # Update the last oldest ID for the next run
    if oldest_id:
        update_last_oldest_id(oldest_id)
        print(f"Updated last oldest story ID to: {oldest_id}\n")
    
    # Save stories to database
    new_count, update_count = save_or_update_stories(stories)
    print(f"Added {new_count} new stories and updated {update_count} existing stories\n")
    
    # Update the last poll time
    update_last_poll_time()
    
    return stories

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description='Poll Hacker News for recent high-quality stories')
    parser.add_argument('--hours', type=int, default=24,
                        help='Number of hours to look back')
    parser.add_argument('--min-score', type=int, default=30,
                        help='Minimum score threshold for displaying stories')
    parser.add_argument('--source', type=str, choices=['top', 'best', 'new'], default='top',
                        help='Source to fetch stories from (top, best, or new)')
    parser.add_argument('--limit', type=int, default=500,
                        help='Maximum number of stories to fetch from source')
    parser.add_argument('--claude', action='store_true',
                        help='Use Claude AI to calculate relevance scores for stories')
    parser.add_argument('--min-relevance', type=int, default=75,
                        help='Minimum relevance score threshold (0-100) when using Claude')
    parser.add_argument('--scored-only', action='store_true',
                        help='Only show stories that already have a relevance score (no new API calls)')
    parser.add_argument('--background-score', action='store_true',
                        help='Use background scoring process instead of inline scoring')
    args = parser.parse_args()
    
    print(f"Polling Hacker News {args.source} stories from the past {args.hours} hours with score >= {args.min_score}...\n")
    
    try:
        # Run the async function in the event loop
        # Handle parameters for optimized relevance filtering
        min_relevance = None
        
        # If we want scored only stories, we can filter directly from the database
        if args.claude and args.scored_only and args.min_relevance > 0:
            min_relevance = args.min_relevance
            print("Using scored-only mode: Only showing stories with existing relevance scores.")
        elif args.claude and args.min_relevance > 0:
            # Otherwise, we'll do a manual filter after potentially calculating new scores
            min_relevance = None
            
        high_score_stories = asyncio.run(poll_hacker_news_async(
            hours=args.hours,
            min_score=args.min_score,
            source=args.source,
            limit=args.limit,
            min_relevance=min_relevance
        ))
        
        if high_score_stories:
            # Apply Claude AI relevance scoring if requested
            if args.claude:
                print("\nUsing Claude AI to filter stories by relevance...")
                
                # First, filter out stories that already have relevance scores
                stories_with_scores = [s for s in high_score_stories if 'relevance_score' in s and s['relevance_score'] is not None]
                unscored_stories = [s for s in high_score_stories if 'relevance_score' not in s or s['relevance_score'] is None]
                
                calculated_count = 0
                
                # Handle different scoring modes
                if args.scored_only:
                    # Scored-only mode - don't calculate new scores
                    print(f"Scored-only mode active. Using {len(stories_with_scores)} stories with existing scores.")
                    print(f"Skipping {len(unscored_stories)} stories without scores.")
                    
                elif args.background_score and unscored_stories:
                    # Background scoring mode - don't calculate scores now but suggest running the background script
                    print(f"Background scoring mode active. Found {len(unscored_stories)} stories without scores.")
                    print("To calculate scores for these stories, run the background scorer:")
                    print(f"python src/background_scorer.py --hours {args.hours} --min-score {args.min_score}")
                    
                    # Include unscored stories in the results but with NULL relevance score
                    stories_with_scores.extend(unscored_stories)
                    
                elif unscored_stories:
                    # Standard inline scoring mode
                    print(f"Found {len(unscored_stories)} stories without relevance scores...")
                    # Process unscored stories in batches
                    batch_size = 10  # Adjust based on API rate limits
                    story_batches = []
                    for i in range(0, len(unscored_stories), batch_size):
                        batch = unscored_stories[i:i + batch_size]
                        if batch:
                            story_batches.append(batch)
                    
                    # Process each batch asynchronously
                    for i, batch in enumerate(story_batches):
                        print(f"Processing batch {i+1}/{len(story_batches)} ({len(batch)} stories)...")
                        # Process the batch asynchronously
                        processed_batch = asyncio.run(process_story_batch_async(batch))
                        stories_with_scores.extend(processed_batch)
                        calculated_count += len(batch)
                        
                        # Update the database after each batch
                        update_story_scores(processed_batch)
                        print(f"Updated database with scores for batch {i+1}.")
                        
                        # Short pause between batches to avoid rate limiting
                        if i < len(story_batches) - 1:
                            print("Pausing briefly before next batch...")
                            time.sleep(1)
                else:
                    print("All stories already have relevance scores. No API calls needed.")
                
                if calculated_count > 0:
                    print(f"Calculated relevance scores for {calculated_count} new stories and updated database.")
                
                # Filter stories by relevance score if not in background mode (which shows all stories)
                if args.background_score:
                    # In background mode, include all stories but mark unscored ones
                    high_score_stories = stories_with_scores
                    for story in high_score_stories:
                        if 'relevance_score' not in story or story['relevance_score'] is None:
                            story['relevance_score'] = None
                else:
                    # Normal mode - filter by relevance score
                    interesting_stories = [s for s in stories_with_scores if s.get('relevance_score', 0) >= args.min_relevance]
                    filtered_out = len(stories_with_scores) - len(interesting_stories)
                    print(f"Relevance filter applied: {len(interesting_stories)} stories above threshold of {args.min_relevance} ({filtered_out} filtered out)\n")
                    high_score_stories = interesting_stories
            
            # Display final results
            if high_score_stories:
                print(f"Top stories from the past {args.hours} hours (score >= {args.min_score}):")
                for story in high_score_stories:
                    print(format_story(story))
            else:
                print(f"No stories matched your criteria from the past {args.hours} hours.")
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