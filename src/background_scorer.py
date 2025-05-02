#!/usr/bin/env python3

"""
Background worker script for calculating relevance scores for HN stories.

This script runs independently from the main polling process and is designed to:
1. Fetch unscored stories from the database
2. Calculate relevance scores in batches
3. Update the database with the new scores

It can be run manually or scheduled via cron/systemd to run periodically.
"""

import os
import sys
import time
import asyncio
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import init_db, get_unscored_stories_in_batches, update_story_scores
from src.classifier import process_story_batch_async

async def score_stories_async(hours=None, min_score=0, batch_size=10, max_stories=None):
    """Score unscored stories from the database.
    
    Args:
        hours (int, optional): Number of hours to look back. If None, processes all unscored stories.
        min_score (int): Minimum score threshold
        batch_size (int): Number of stories to process in each batch
        max_stories (int, optional): Maximum number of stories to process in total
        
    Returns:
        int: Number of stories scored
    """
    print(f"[{datetime.now().isoformat()}] Starting background scoring...")
    
    # Initialize database if not exists
    init_db()
    
    # Get batches of unscored stories
    story_batches = get_unscored_stories_in_batches(hours=hours, min_score=min_score, batch_size=batch_size)
    
    if not story_batches:
        print(f"[{datetime.now().isoformat()}] No unscored stories found. Exiting.")
        return 0
    
    print(f"[{datetime.now().isoformat()}] Found {sum(len(batch) for batch in story_batches)} unscored stories in {len(story_batches)} batches.")
    
    # Limit the number of stories if requested
    if max_stories is not None:
        stories_to_process = 0
        limited_batches = []
        
        for batch in story_batches:
            if stories_to_process + len(batch) <= max_stories:
                limited_batches.append(batch)
                stories_to_process += len(batch)
            else:
                # Take partial batch if needed
                remaining = max_stories - stories_to_process
                if remaining > 0:
                    limited_batches.append(batch[:remaining])
                    stories_to_process += remaining
                break
        
        story_batches = limited_batches
        print(f"[{datetime.now().isoformat()}] Limited to {stories_to_process} stories ({len(story_batches)} batches).")
    
    total_scored = 0
    
    # Process each batch asynchronously
    for i, batch in enumerate(story_batches):
        start_time = time.time()
        print(f"[{datetime.now().isoformat()}] Processing batch {i+1}/{len(story_batches)} ({len(batch)} stories)...")
        
        # Process the batch
        processed_batch = await process_story_batch_async(batch)
        
        # Update the database
        update_story_scores(processed_batch)
        
        elapsed = time.time() - start_time
        total_scored += len(batch)
        print(f"[{datetime.now().isoformat()}] Batch {i+1} completed in {elapsed:.2f} seconds. {total_scored} stories scored so far.")
        
        # Pause between batches to avoid rate limiting
        if i < len(story_batches) - 1:
            pause_time = max(1, min(5, 10 - elapsed))  # Dynamic pause: 1-5 seconds
            print(f"[{datetime.now().isoformat()}] Pausing for {pause_time:.1f} seconds before next batch...")
            time.sleep(pause_time)
    
    print(f"[{datetime.now().isoformat()}] Background scoring completed. Scored {total_scored} stories.")
    return total_scored

def main():
    """Main entry point for the program."""
    parser = argparse.ArgumentParser(description='Calculate relevance scores for unscored HN stories')
    parser.add_argument('--hours', type=int, default=None,
                        help='Number of hours to look back (default: all unscored stories)')
    parser.add_argument('--min-score', type=int, default=0,
                        help='Minimum score threshold (default: 0, include all stories)')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Number of stories to process in each batch (default: 10)')
    parser.add_argument('--max-stories', type=int, default=None,
                        help='Maximum number of stories to process in total (default: no limit)')
    args = parser.parse_args()
    
    try:
        asyncio.run(score_stories_async(
            hours=args.hours,
            min_score=args.min_score,
            batch_size=args.batch_size,
            max_stories=args.max_stories
        ))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())