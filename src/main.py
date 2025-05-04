#!/usr/bin/env python3

import sys
import os
import argparse
import asyncio
import time
import math
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any, Union, cast

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

def calculate_combined_score(story: Dict[str, Any], hn_weight: float = 0.7) -> float:
    """Calculate a combined score using both HN score and relevance score.
    
    Uses logarithmic scaling for HN score to reduce the impact of extremely high scores,
    then combines it with the relevance score using a weighted average.
    
    Args:
        story (Dict[str, Any]): Story details including 'score' and optionally 'relevance_score'
        hn_weight (float): Weight to apply to the normalized HN score (0.0-1.0)
        
    Returns:
        float: Combined score between 0-100
    """
    # Extract scores from story
    hn_score = story.get('score', 0)
    relevance_score = story.get('relevance_score', 0)
    
    # If no relevance score, fall back to just using HN score
    if relevance_score is None:
        relevance_score = 0
    
    # Normalize the HN score using logarithmic scale (log10(1000) ≈ 3, log10(10000) ≈ 4)
    # Scale to approximately 0-100 range
    normalized_hn = math.log10(max(1, hn_score)) * 25
    
    # Combine with weighted average
    relevance_weight = 1 - hn_weight
    return (hn_weight * normalized_hn) + (relevance_weight * relevance_score)

def format_story(story: Dict[str, Any]) -> str:
    """Format a story for console output.
    
    Args:
        story (Dict[str, Any]): Story details
        
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
    
    # Include scores information
    score_info = f"HN Score: {score}"
    if 'relevance_score' in story and story['relevance_score'] is not None:
        score_info += f" | Relevance: {story['relevance_score']}"
    if 'combined_score' in story:
        score_info += f" | Combined: {story['combined_score']:.1f}"
    
    output += f"ID: {story_id} | {score_info} | By: {author} | Posted: {time_str}\n"
    
    if url:
        output += f"URL: {url}\n"
    else:
        # If no URL, it's probably an Ask HN post
        output += f"URL: https://news.ycombinator.com/item?id={story['id']}\n"
    
    return output

async def fetch_stories_async(hours: int = 24, min_score: int = 30, source: str = 'top', limit: int = 500) -> Tuple[int, int]:
    """Fetch stories from Hacker News and save to the database.
    
    Args:
        hours (int): Number of hours to look back
        min_score (int): Minimum score threshold for displaying stories
        source (str): Source to use - 'top', 'best', or 'new'
        limit (int): Maximum number of stories to fetch from source
        
    Returns:
        Tuple[int, int]: (new_count, update_count) - Number of new and updated stories
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
    
    return new_count, update_count

async def score_stories_async(hours: int = 24, min_score: int = 30, batch_size: int = 10) -> int:
    """Calculate relevance scores for unscored stories.
    
    Args:
        hours (int): Number of hours to look back for unscored stories
        min_score (int): Minimum HN score threshold for stories to score
        batch_size (int): Number of stories to process in each batch
        
    Returns:
        int: Number of stories scored
    """
    # Initialize database if not exists
    init_db()
    
    # Get batches of unscored stories
    story_batches = get_unscored_stories_in_batches(hours=hours, min_score=min_score, batch_size=batch_size)
    
    if not story_batches:
        print("No unscored stories found that meet the criteria.")
        return 0
    
    total_stories = sum(len(batch) for batch in story_batches)
    print(f"Found {total_stories} unscored stories in {len(story_batches)} batches.")
    
    scored_count = 0
    
    # Process each batch asynchronously
    for i, batch in enumerate(story_batches):
        print(f"Processing batch {i+1}/{len(story_batches)} ({len(batch)} stories)...")
        
        # Process the batch asynchronously
        processed_batch = await process_story_batch_async(batch)
        scored_count += len(processed_batch)
        
        # Update the database after each batch
        update_story_scores(processed_batch)
        print(f"Updated database with scores for batch {i+1}.")
        
        # Short pause between batches to avoid rate limiting
        if i < len(story_batches) - 1:
            print("Pausing briefly before next batch...")
            time.sleep(1)
    
    print(f"\nCalculated relevance scores for {scored_count} stories and updated database.")
    return scored_count

def show_stories(hours: int = 24, min_hn_score: int = 30, min_relevance: int = 75, hn_weight: float = 0.7) -> int:
    """Display stories meeting criteria from the database.
    
    Args:
        hours (int): Number of hours to look back
        min_hn_score (int): Minimum HN score threshold
        min_relevance (int): Minimum relevance score threshold
        hn_weight (float): Weight to apply to HN score in combined scoring (0.0-1.0)
        
    Returns:
        int: Number of stories displayed
    """
    # Initialize database if not exists
    init_db()
    
    # Get stories matching criteria
    print(f"Finding stories from the past {hours} hours with HN score >= {min_hn_score} and relevance score >= {min_relevance}...")
    
    # First get all stories with minimum HN score
    all_stories = get_stories_within_timeframe(hours=hours, min_score=min_hn_score)
    
    if not all_stories:
        print(f"No stories found with HN score >= {min_hn_score} from the past {hours} hours.")
        return 0
    
    # Filter by relevance score
    stories_with_relevance = [s for s in all_stories if 'relevance_score' in s and s['relevance_score'] is not None]
    relevant_stories = [s for s in stories_with_relevance if s['relevance_score'] >= min_relevance]
    
    # Get stats for output
    unscored_count = len(all_stories) - len(stories_with_relevance)
    filtered_out = len(stories_with_relevance) - len(relevant_stories)
    
    # Print stats
    print(f"Found {len(all_stories)} stories with HN score >= {min_hn_score}")
    print(f"Of these, {len(stories_with_relevance)} have relevance scores ({unscored_count} unscored)")
    print(f"After filtering: {len(relevant_stories)} stories with relevance >= {min_relevance} ({filtered_out} filtered out)\n")
    
    # Display stories
    if relevant_stories:
        # Calculate combined scores for all stories
        for story in relevant_stories:
            story['combined_score'] = calculate_combined_score(story, hn_weight)
        
        # Sort by combined score
        relevant_stories.sort(key=lambda s: s['combined_score'], reverse=True)
        
        print(f"Top stories from the past {hours} hours (HN score >= {min_hn_score}, relevance >= {min_relevance}):")
        print(f"Sorted using combined score (HN weight: {hn_weight:.1f}, Relevance weight: {1-hn_weight:.1f})")
        for story in relevant_stories:
            print(format_story(story))
    else:
        print(f"No stories matched your criteria from the past {hours} hours.")
    
    return len(relevant_stories)

def cmd_fetch(args: argparse.Namespace) -> int:
    """Handle the 'fetch' subcommand."""
    print(f"Fetching stories from Hacker News {args.source}...")
    new_count, update_count = asyncio.run(fetch_stories_async(
        hours=args.hours,
        min_score=args.min_score,
        source=args.source,
        limit=args.limit
    ))
    print(f"Done! Added {new_count} new stories and updated {update_count} existing stories.")
    return 0

def cmd_score(args: argparse.Namespace) -> int:
    """Handle the 'score' subcommand."""
    print("Calculating relevance scores for unscored stories...")
    scored_count = asyncio.run(score_stories_async(
        hours=args.hours,
        min_score=args.min_score,
        batch_size=args.batch_size
    ))
    print(f"Done! Calculated relevance scores for {scored_count} stories.")
    return 0

def cmd_show(args: argparse.Namespace) -> int:
    """Handle the 'show' subcommand."""
    show_stories(
        hours=args.hours,
        min_hn_score=args.min_score,
        min_relevance=args.min_relevance,
        hn_weight=args.hn_weight
    )
    return 0

def main() -> int:
    """Main entry point for the program.
    
    Returns:
        int: Exit code (0 for success, non-zero for error)
    """
    # Create the top-level parser
    parser = argparse.ArgumentParser(
        description='Hacker News story poller and relevance filter',
        epilog='Run without a command or with "show" to display stories'
    )
    
    # Create subparsers for each command
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Common arguments
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('--hours', type=int, default=24,
                            help='Number of hours to look back (default: 24)')
    common_parser.add_argument('--min-score', type=int, default=30,
                            help='Minimum HN score threshold (default: 30)')
    
    # 'fetch' command
    fetch_parser = subparsers.add_parser('fetch', parents=[common_parser],
                                     help='Fetch stories from Hacker News')
    fetch_parser.add_argument('--source', type=str, choices=['top', 'best', 'new'], default='top',
                          help='Source to fetch stories from (default: top)')
    fetch_parser.add_argument('--limit', type=int, default=500,
                          help='Maximum number of stories to fetch (default: 500)')
    fetch_parser.set_defaults(func=cmd_fetch)
    
    # 'score' command
    score_parser = subparsers.add_parser('score', parents=[common_parser],
                                     help='Calculate relevance scores for unscored stories')
    score_parser.add_argument('--batch-size', type=int, default=10,
                          help='Number of stories to process in each batch (default: 10)')
    score_parser.set_defaults(func=cmd_score)
    
    # 'show' command
    show_parser = subparsers.add_parser('show', parents=[common_parser],
                                    help='Display stories meeting criteria')
    show_parser.add_argument('--min-relevance', type=int, default=75,
                         help='Minimum relevance score threshold (default: 75)')
    show_parser.add_argument('--hn-weight', type=float, default=0.7,
                         help='Weight to apply to HN score (0.0-1.0, default: 0.7)')
    show_parser.set_defaults(func=cmd_show)
    
    # Parse arguments
    args = parser.parse_args()
    
    try:
        # Initialize the database in any case
        init_db()
        
        # If no command specified, default to 'show'
        if not args.command:
            # Create default args for show command
            args.hours = 24  # Default hours
            args.min_score = 30  # Default min score
            args.min_relevance = 75  # Default min relevance
            args.hn_weight = 0.7  # Default HN weight
            return cmd_show(args)
        
        # Otherwise, run the appropriate command
        return args.func(args)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())