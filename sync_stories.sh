#!/bin/bash

# HN to Readwise sync script
# This script fetches top HN stories, scores them for relevance, and syncs the most relevant ones to Readwise

# Exit on any error
set -e

# Default values
HOURS=24
MIN_SCORE=30
MIN_COMMENTS=30
MIN_RELEVANCE=75
MAX_STORIES=30
SOURCE="top"
CLEANUP=false
BATCH_SIZE=50
MAX_BATCHES=5

# Process command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --hours)
      HOURS="$2"
      shift 2
      ;;
    --min-score)
      MIN_SCORE="$2"
      shift 2
      ;;
    --min-comments)
      MIN_COMMENTS="$2"
      shift 2
      ;;
    --min-relevance)
      MIN_RELEVANCE="$2"
      shift 2
      ;;
    --max-stories)
      MAX_STORIES="$2"
      shift 2
      ;;
    --source)
      SOURCE="$2"
      shift 2
      ;;
    --cleanup)
      CLEANUP=true
      shift
      ;;
    --batch-size)
      BATCH_SIZE="$2"
      shift 2
      ;;
    --max-batches)
      MAX_BATCHES="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "===== HN to Readwise Sync ====="
echo "Configured with:"
echo "- Hours: $HOURS"
echo "- Min Score: $MIN_SCORE"
echo "- Min Comments: $MIN_COMMENTS"
echo "- Min Relevance: $MIN_RELEVANCE"
echo "- Max Stories: $MAX_STORIES"
echo "- Source: $SOURCE"
echo "- Database cleanup: $CLEANUP"
if [ "$CLEANUP" = true ]; then
  echo "  - Batch size: $BATCH_SIZE"
  echo "  - Max batches: $MAX_BATCHES"
fi
echo "=============================="

echo "Step 1: Fetching top stories from Hacker News..."
uv run python -m src.main fetch --hours "$HOURS" --min-score "$MIN_SCORE" --source "$SOURCE"

echo "Step 2: Scoring stories for relevance..."
uv run python -m src.main score --hours "$HOURS" --min-score "$MIN_SCORE" --min-comments "$MIN_COMMENTS" --extract-content

echo "Step 3: Syncing top stories to Readwise Reader..."
uv run python -m src.main sync --hours "$HOURS" --min-score "$MIN_SCORE" --min-comments "$MIN_COMMENTS" --min-relevance "$MIN_RELEVANCE" --max-stories "$MAX_STORIES"

# Optional database cleanup
if [ "$CLEANUP" = true ]; then
  echo "Step 4: Cleaning database of non-existent stories..."
  uv run python -m src.main clean --batch-size "$BATCH_SIZE" --max-batches "$MAX_BATCHES"
fi

echo "Done! The most relevant stories have been synced to your Readwise Reader account."
echo "You can view them at: https://readwise.io/reader"
