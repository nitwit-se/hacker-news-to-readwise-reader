#!/bin/bash

# cron_sync.sh - A wrapper script for running sync_stories.sh from cron
# This script captures all stdout/stderr to a log file and only emails errors

# Get the directory where this script is located
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# The path to the main sync script
SYNC_SCRIPT="$SCRIPT_DIR/sync_stories.sh"

# Ensure the script is executable
chmod +x "$SYNC_SCRIPT"

# Run the sync script with the --quiet flag and any additional arguments
# This will only output errors to stderr, which cron will email
"$SYNC_SCRIPT" --quiet "$@"

# The exit code will be passed through from the sync script
exit $?