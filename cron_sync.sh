#!/bin/bash

# cron_sync.sh - A wrapper script for running sync_stories.sh from cron
# This script captures all stdout/stderr to a log file and only emails errors

# Get the directory where this script is located
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# The path to the main sync script
SYNC_SCRIPT="$SCRIPT_DIR/sync_stories.sh"

# Ensure the script is executable
chmod +x "$SYNC_SCRIPT"

# Load virtual environment if it exists
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Verify necessary tools and environment variables are available
which uv &>/dev/null || { echo "Error: 'uv' not found in PATH. Please install it or update your PATH."; exit 1; }

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "Warning: ANTHROPIC_API_KEY environment variable not set. Relevance scoring may fail." >&2
fi

if [ -z "$READWISE_API_KEY" ]; then
    echo "Warning: READWISE_API_KEY environment variable not set. Syncing to Readwise will fail." >&2
fi

# Run the sync script with the --quiet flag and any additional arguments
# This will only output errors to stderr, which cron will email
"$SYNC_SCRIPT" --quiet "$@"

# The exit code will be passed through from the sync script
exit $?