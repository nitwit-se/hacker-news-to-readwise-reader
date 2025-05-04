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
from src.db import get_unsynced_stories, mark_stories_as_synced, update_last_readwise_sync_time
from src.db import get_readwise_sync_stats
from src.api import get_stories_until_cutoff, get_stories_details_async, get_stories_from_maxitem
from src.api import get_filtered_stories_async
from src.classifier import is_interesting, get_relevance_score
from src.classifier import process_story_batch_async, get_relevance_score_async
from src.readwise import batch_add_to_readwise, ReadwiseError

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

async def score_stories_async(hours: int = 24, min_score: int = 30, batch_size: int = 10, use_content_extraction: bool = False) -> int:
    """Calculate relevance scores for unscored stories.
    
    Args:
        hours (int): Number of hours to look back for unscored stories
        min_score (int): Minimum HN score threshold for stories to score
        batch_size (int): Number of stories to process in each batch
        use_content_extraction (bool): Whether to extract and use article content
        
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
    
    if use_content_extraction:
        print("Content extraction is enabled. This will download and analyze the full text of each article.")
        print("This process will be slower but should provide more accurate scoring.")
        # Reduce batch size if content extraction is enabled to avoid overloading
        if batch_size > 5:
            batch_size = 5
            print(f"Reducing batch size to {batch_size} to avoid overloading with content extraction.")
    
    scored_count = 0
    
    # Process each batch asynchronously
    for i, batch in enumerate(story_batches):
        print(f"Processing batch {i+1}/{len(story_batches)} ({len(batch)} stories)...")
        
        # Process the batch asynchronously
        processed_batch = await process_story_batch_async(batch, use_content_extraction=use_content_extraction)
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
    if args.extract_content:
        print("Content extraction enabled - this may take longer but should provide more accurate scoring")
    
    scored_count = asyncio.run(score_stories_async(
        hours=args.hours,
        min_score=args.min_score,
        batch_size=args.batch_size,
        use_content_extraction=args.extract_content
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

def sync_with_readwise(hours: int = 24, min_hn_score: int = 30, min_relevance: int = 75, batch_size: int = 10, max_stories: Optional[int] = None) -> int:
    """Sync stories to Readwise Reader with relevance filtering.
    
    Args:
        hours (int): Number of hours to look back
        min_hn_score (int): Minimum HN score threshold
        min_relevance (int): Minimum relevance score threshold (defaults to 75)
        batch_size (int): Number of stories to process in each batch
        max_stories (Optional[int]): Maximum number of stories to sync (useful for testing)
        
    Returns:
        int: Number of stories synced
    """
    # Initialize database if not exists
    init_db()
    
    print(f"Finding unsynced stories from the past {hours} hours with HN score >= {min_hn_score}")
    print(f"and relevance score >= {min_relevance}...")
    
    # Get unsynced stories matching criteria
    stories = get_unsynced_stories(hours=hours, min_score=min_hn_score, min_relevance=min_relevance)
    
    if not stories:
        print("No unsynced stories found matching your criteria.")
        return 0
    
    # Apply max_stories limit if specified
    if max_stories and len(stories) > max_stories:
        print(f"Limiting to {max_stories} stories (out of {len(stories)} found)")
        stories = stories[:max_stories]
    
    print(f"Found {len(stories)} unsynced stories to process.")
    
    # Check for Readwise API key
    if "READWISE_API_KEY" not in os.environ:
        print("Error: READWISE_API_KEY environment variable not set.")
        print("Please set it to your Readwise Reader API key before running this command.")
        return 1
    
    # Fetch all existing URLs from Readwise Reader once at the start
    try:
        print("Fetching all documents from Readwise Reader...")
        from src.readwise import get_all_readwise_urls
        existing_urls = get_all_readwise_urls()
        print(f"Found {len(existing_urls)} documents in Readwise Reader")
    except Exception as e:
        print(f"Failed to fetch existing URLs: {e}")
        print("Will continue without pre-checking for duplicates.")
        existing_urls = set()
    
    # Process stories in batches
    synced_count = 0
    failed_ids = []
    total_batches = math.ceil(len(stories) / batch_size)
    
    for i in range(0, len(stories), batch_size):
        batch = stories[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} stories)...")
        
        try:
            # Add the batch to Readwise, using our pre-fetched URL set
            added_ids, batch_failed_ids = batch_add_to_readwise(batch, existing_urls=existing_urls)
            
            # Update database for successfully synced stories
            if added_ids:
                marked_count = mark_stories_as_synced(added_ids)
                synced_count += marked_count
                print(f"Synced {marked_count} stories to Readwise Reader.")
            
            # Record any failures
            if batch_failed_ids:
                failed_ids.extend(batch_failed_ids)
                print(f"Failed to sync {len(batch_failed_ids)} stories in this batch.")
                
            # Pause between batches
            if batch_num < total_batches:
                print("Pausing briefly before next batch...")
                time.sleep(2)  # Increased pause time to avoid rate limiting
                
        except Exception as e:
            print(f"Error syncing with Readwise: {e}")
            # Add all batch IDs to failed list
            for story in batch:
                failed_ids.append((story.get('id'), str(e)))
    
    # Update the last sync time
    if synced_count > 0:
        update_last_readwise_sync_time()
    
    # Final stats
    print(f"\nSynced {synced_count} stories to Readwise Reader.")
    if failed_ids:
        print(f"Failed to sync {len(failed_ids)} stories.")
        
    # Show sync stats
    stats = get_readwise_sync_stats()
    print(f"\nReadwise sync statistics:")
    print(f"Total stories in database: {stats['total_stories']}")
    print(f"Synced stories: {stats['synced_stories']}")
    print(f"Unsynced stories: {stats['unsynced_stories']}")
    print(f"Last sync time: {stats['last_sync_time']}")
    
    return synced_count

def cmd_sync(args: argparse.Namespace) -> int:
    """Handle the 'sync' subcommand."""
    print("Syncing stories with Readwise Reader...")
    
    # Apply relevance filter by default, unless --no-relevance-filter is specified
    min_relevance = None if args.no_relevance_filter else args.min_relevance
    
    if args.no_relevance_filter:
        print("Relevance filtering is disabled - all stories matching HN score criteria will be synced")
    else:
        print(f"Relevance filtering is enabled - only stories with relevance score >= {args.min_relevance} will be synced")
    
    if args.max_stories:
        print(f"Maximum number of stories to sync: {args.max_stories}")
    
    # Ensure reasonable batch size to avoid rate limiting
    batch_size = min(args.batch_size, 5)
    if batch_size != args.batch_size:
        print(f"Reducing batch size to {batch_size} to avoid rate limiting")
    
    synced_count = sync_with_readwise(
        hours=args.hours,
        min_hn_score=args.min_score,
        min_relevance=min_relevance,
        batch_size=batch_size,
        max_stories=args.max_stories
    )
    
    if synced_count > 0:
        print(f"Done! Synced {synced_count} stories to Readwise Reader.")
    else:
        print("No stories were synced to Readwise Reader.")
        
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
    score_parser.add_argument('--extract-content', action='store_true',
                          help='Extract and analyze article content for more accurate scoring')
    score_parser.set_defaults(func=cmd_score)
    
    # 'show' command
    show_parser = subparsers.add_parser('show', parents=[common_parser],
                                    help='Display stories meeting criteria')
    show_parser.add_argument('--min-relevance', type=int, default=75,
                         help='Minimum relevance score threshold (default: 75)')
    show_parser.add_argument('--hn-weight', type=float, default=0.7,
                         help='Weight to apply to HN score (0.0-1.0, default: 0.7)')
    show_parser.set_defaults(func=cmd_show)
    
    # 'sync' command
    sync_parser = subparsers.add_parser('sync', parents=[common_parser],
                                    help='Sync stories to Readwise Reader')
    sync_parser.add_argument('--min-relevance', type=int, default=75,
                         help='Minimum relevance score threshold (default: 75)')
    sync_parser.add_argument('--batch-size', type=int, default=10,
                         help='Number of stories to process in each batch (default: 10)')
    sync_parser.add_argument('--max-stories', type=int,
                         help='Maximum number of stories to sync (useful for testing)')
    sync_parser.add_argument('--no-relevance-filter', action='store_true',
                         help='Disable relevance filtering (by default, only stories with relevance scores >= min-relevance are synced)')
    sync_parser.set_defaults(func=cmd_sync)
    
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