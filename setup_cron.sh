#!/bin/bash

# setup_cron.sh - Helper script to set up crontab entry for the Hacker News poller

# Exit on any error
set -e

# Get the directory where this script is located (project directory)
PROJECT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

# Function to prompt for values
prompt_for_value() {
    local prompt_text="$1"
    local default_value="$2"
    local var_name="$3"
    
    read -p "$prompt_text [$default_value]: " input
    if [ -z "$input" ]; then
        eval "$var_name=\"$default_value\""
    else
        eval "$var_name=\"$input\""
    fi
}

# Check if API keys are set in environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ANTHROPIC_API_KEY is not set in your environment."
    echo "This is required for relevance scoring with Claude AI."
    read -p "Would you like to set it now? (y/n) [y]: " set_anthropic
    set_anthropic=${set_anthropic:-y}
    
    if [[ "$set_anthropic" == "y" || "$set_anthropic" == "Y" ]]; then
        read -p "Enter your Anthropic API key: " ANTHROPIC_API_KEY
    else
        echo "Warning: Relevance scoring will not work without an Anthropic API key."
    fi
fi

if [ -z "$READWISE_API_KEY" ]; then
    echo "READWISE_API_KEY is not set in your environment."
    echo "This is required for syncing stories to Readwise Reader."
    read -p "Would you like to set it now? (y/n) [y]: " set_readwise
    set_readwise=${set_readwise:-y}
    
    if [[ "$set_readwise" == "y" || "$set_readwise" == "Y" ]]; then
        read -p "Enter your Readwise API key: " READWISE_API_KEY
    else
        echo "Warning: Syncing to Readwise will not work without a Readwise API key."
    fi
fi

# Configure cron schedule
echo "Configure the cron schedule:"
prompt_for_value "How often should the script run? (hourly, daily, custom)" "hourly" SCHEDULE

case "$SCHEDULE" in
    hourly)
        prompt_for_value "Which minute of the hour should it run? (0-59)" "15" MINUTE
        CRON_SCHEDULE="$MINUTE * * * *"
        ;;
    daily)
        prompt_for_value "Which hour of the day should it run? (0-23)" "3" HOUR
        prompt_for_value "Which minute of the hour should it run? (0-59)" "15" MINUTE
        CRON_SCHEDULE="$MINUTE $HOUR * * *"
        ;;
    custom)
        read -p "Enter a custom cron schedule (minute hour day month weekday): " CRON_SCHEDULE
        ;;
    *)
        echo "Unknown schedule type. Using hourly at minute 15."
        CRON_SCHEDULE="15 * * * *"
        ;;
esac

# Configure script options
echo "Configure script options:"
prompt_for_value "Hours to look back for stories" "24" HOURS
prompt_for_value "Minimum score threshold" "30" MIN_SCORE
prompt_for_value "Minimum comments threshold" "30" MIN_COMMENTS
prompt_for_value "Minimum relevance score" "75" MIN_RELEVANCE
prompt_for_value "Maximum stories to sync" "10" MAX_STORIES
prompt_for_value "Source (top, best, new)" "top" SOURCE

read -p "Enable database cleanup? (y/n) [y]: " enable_cleanup
enable_cleanup=${enable_cleanup:-y}

if [[ "$enable_cleanup" == "y" || "$enable_cleanup" == "Y" ]]; then
    CLEANUP_FLAG="--cleanup"
else
    CLEANUP_FLAG=""
fi

# Generate crontab entry
CRONTAB_ENTRY="# Hacker News Poller - Added $(date)"

# Environment variables
if [ -n "$ANTHROPIC_API_KEY" ]; then
    CRONTAB_ENTRY="$CRONTAB_ENTRY
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY"
fi

if [ -n "$READWISE_API_KEY" ]; then
    CRONTAB_ENTRY="$CRONTAB_ENTRY
READWISE_API_KEY=$READWISE_API_KEY"
fi

# Add the cron command
CRONTAB_ENTRY="$CRONTAB_ENTRY
$CRON_SCHEDULE cd '$PROJECT_DIR' && ./cron_sync.sh --hours $HOURS --min-score $MIN_SCORE --min-comments $MIN_COMMENTS --min-relevance $MIN_RELEVANCE --max-stories $MAX_STORIES --source $SOURCE $CLEANUP_FLAG"

# Display the crontab entry
echo -e "\n--- Generated Crontab Entry ---"
echo "$CRONTAB_ENTRY"
echo -e "------------------------------\n"

# Ask if user wants to install the crontab entry
read -p "Would you like to install this crontab entry now? (y/n) [y]: " install_crontab
install_crontab=${install_crontab:-y}

if [[ "$install_crontab" == "y" || "$install_crontab" == "Y" ]]; then
    # Create a temporary file with current crontab
    TEMP_CRONTAB=$(mktemp)
    crontab -l > "$TEMP_CRONTAB" 2>/dev/null || true
    
    # Check if the entry already exists (approximately)
    if grep -q "cd '$PROJECT_DIR' && ./cron_sync.sh" "$TEMP_CRONTAB"; then
        read -p "A similar crontab entry already exists. Replace it? (y/n) [n]: " replace_entry
        replace_entry=${replace_entry:-n}
        
        if [[ "$replace_entry" == "y" || "$replace_entry" == "Y" ]]; then
            # Remove existing entry and add new one
            grep -v "cd '$PROJECT_DIR' && ./cron_sync.sh" "$TEMP_CRONTAB" > "${TEMP_CRONTAB}.new"
            echo "$CRONTAB_ENTRY" >> "${TEMP_CRONTAB}.new"
            crontab "${TEMP_CRONTAB}.new"
            rm -f "${TEMP_CRONTAB}.new"
        else
            echo "Leaving existing crontab entry unchanged."
        fi
    else
        # Add new entry
        echo "$CRONTAB_ENTRY" >> "$TEMP_CRONTAB"
        crontab "$TEMP_CRONTAB"
    fi
    
    rm -f "$TEMP_CRONTAB"
    echo "Crontab entry installed successfully!"
else
    echo "To install the crontab entry manually, run:"
    echo "crontab -e"
    echo "And add the entry shown above."
fi

echo "Setup complete! The script will run according to the schedule you specified."
echo "Log files will be stored at: ~/.hn-sync/logs/hn_sync.log"