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
QUIET=false
LOG_FILE="$HOME/.hn-sync/logs/hn_sync.log"
LOG_DIR="$HOME/.hn-sync/logs"

# Create the log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Logging functions
log_info() {
  local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo "[INFO] $timestamp: $*" >> "$LOG_FILE"
  if [ "$QUIET" = false ]; then
    echo "[INFO] $*"
  fi
}

log_error() {
  local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo "[ERROR] $timestamp: $*" >> "$LOG_FILE"
  # Always output errors, even in quiet mode
  echo "[ERROR] $*" >&2
}

log_success() {
  local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
  echo "[SUCCESS] $timestamp: $*" >> "$LOG_FILE"
  if [ "$QUIET" = false ]; then
    echo "[SUCCESS] $*"
  fi
}

# Rotate log file if it gets too large (> 1MB)
# Use a cross-platform way to check file size
get_file_size() {
  if command -v stat &>/dev/null; then
    # Try GNU stat (Linux)
    if stat --version &>/dev/null 2>&1; then
      stat --format="%s" "$1" 2>/dev/null
    # Try BSD stat (macOS)
    elif stat -f%z "$1" &>/dev/null 2>&1; then
      stat -f%z "$1"
    else
      # Fallback: use wc -c
      wc -c < "$1"
    fi
  else
    # Fallback: use wc -c
    wc -c < "$1"
  fi
}

if [ -f "$LOG_FILE" ]; then
  file_size=$(get_file_size "$LOG_FILE")
  if [ -n "$file_size" ] && [ "$file_size" -gt 1048576 ]; then
    # Compress and move the current log to log.1.gz, log.2.gz, etc.
    for i in {4..1}; do
      if [ -f "$LOG_FILE.$i.gz" ]; then
        mv "$LOG_FILE.$i.gz" "$LOG_FILE.$((i+1)).gz"
      fi
    done
    if [ -f "$LOG_FILE" ]; then
      gzip -c "$LOG_FILE" > "$LOG_FILE.1.gz"
      : > "$LOG_FILE"  # Clear the log file
      log_info "Log file rotated"
    fi
  fi
fi

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
    --quiet|--silent)
      QUIET=true
      shift
      ;;
    --log-file)
      LOG_FILE="$2"
      shift 2
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

log_info "===== HN to Readwise Sync ====="
log_info "Configured with:"
log_info "- Hours: $HOURS"
log_info "- Min Score: $MIN_SCORE"
log_info "- Min Comments: $MIN_COMMENTS"
log_info "- Min Relevance: $MIN_RELEVANCE"
log_info "- Max Stories: $MAX_STORIES"
log_info "- Source: $SOURCE"
log_info "- Database cleanup: $CLEANUP"
log_info "- Log file: $LOG_FILE"
if [ "$CLEANUP" = true ]; then
  log_info "  - Batch size: $BATCH_SIZE"
  log_info "  - Max batches: $MAX_BATCHES"
fi
log_info "=============================="

# Capture command output while also logging it
run_command() {
  local cmd="$1"
  local step_name="$2"
  local start_time=$(date +%s)
  
  log_info "Step: $step_name"
  log_info "Running: $cmd"
  
  # Run the command and capture output
  local output
  if ! output=$(eval "$cmd" 2>&1); then
    log_error "Failed to execute: $cmd"
    log_error "Output: $output"
    return 1
  fi
  
  # Log the output if not in quiet mode
  if [ "$QUIET" = false ]; then
    echo "$output"
  fi
  
  # Always log the output to the log file
  echo "$output" >> "$LOG_FILE"
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  log_info "Completed: $step_name (took ${duration}s)"
  
  return 0
}

# Step 1: Fetch
if ! run_command "uv run python -m src.main fetch --hours \"$HOURS\" --min-score \"$MIN_SCORE\" --source \"$SOURCE\"" "Fetching top stories from Hacker News"; then
  log_error "Failed to fetch stories"
  exit 1
fi

# Step 2: Score
if ! run_command "uv run python -m src.main score --hours \"$HOURS\" --min-score \"$MIN_SCORE\" --min-comments \"$MIN_COMMENTS\" --extract-content" "Scoring stories for relevance"; then
  log_error "Failed to score stories"
  exit 1
fi

# Step 3: Sync
if ! run_command "uv run python -m src.main sync --hours \"$HOURS\" --min-score \"$MIN_SCORE\" --min-comments \"$MIN_COMMENTS\" --min-relevance \"$MIN_RELEVANCE\" --max-stories \"$MAX_STORIES\"" "Syncing top stories to Readwise Reader"; then
  log_error "Failed to sync stories"
  exit 1
fi

# Optional database cleanup
if [ "$CLEANUP" = true ]; then
  if ! run_command "uv run python -m src.main clean --batch-size \"$BATCH_SIZE\" --max-batches \"$MAX_BATCHES\"" "Cleaning database of non-existent stories"; then
    log_error "Failed to clean database"
    exit 1
  fi
fi

log_success "Done! The most relevant stories have been synced to your Readwise Reader account."
log_info "You can view them at: https://readwise.io/reader"
