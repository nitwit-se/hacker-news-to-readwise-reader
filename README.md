# Hacker News Poller

A Python application that polls Hacker News for new stories since the last poll and displays them in the console. Story data is stored in a SQLite database for tracking purposes.

## Features

- Fetches new stories from Hacker News API
- Stores story data in a local SQLite database
- Fetches content from story URLs and converts to markdown
- Implements robust error handling with retry mechanism
- Special handling for sites that block content fetching (e.g., Twitter/X)
- Tracks when the application was last run
- Displays new stories with content summaries in the console

## Requirements

- Python 3.12+
- `uv` Python package manager

## Installation

1. Clone this repository

2. Use the setup script (recommended):
   ```
   # Run the setup script
   ./setup.sh
   ```

   Or set up manually with `uv`:
   ```
   # Create a virtual environment
   uv venv
   
   # Activate the environment (bash/zsh)
   source .venv/bin/activate
   
   # Or for fish shell
   source .venv/bin/activate.fish
   
   # Install the package in development mode
   uv pip install -e .
   
   # For development dependencies
   uv pip install -e ".[dev]"
   ```

## Usage

To poll for new stories:

```
# Activate the environment if not already activated
# For bash/zsh
source .venv/bin/activate

# For fish shell
source .venv/bin/activate.fish

# Run using the installed command
hn-poll

# Or run directly
python src/main.py
```

Options:

- `--limit N`: Specify maximum number of stories to retrieve (default: 30)
- `--content-limit N`: Maximum number of stories to fetch content for (default: 5)
- `--skip-content`: Skip fetching content for stories
- `--retry-failed`: Retry fetching content for stories that previously failed

## How It Works

1. The program checks when it was last run (stored in the SQLite database)
2. It fetches new stories from the Hacker News API
3. New stories are stored in the database
4. For a configurable number of stories, the content at the URLs is fetched and converted to markdown:
   - New stories are prioritized for content fetching
   - URLs from sites that block content fetching (like Twitter) are automatically skipped
   - Transient errors are retried with exponential backoff
   - Error information is tracked in the database
5. The content and error details are stored in the database for future reference
6. Stories that are new since the last poll are displayed in the console with content summaries
7. Custom messages are shown for URLs with unavailable content

## Database

The application uses SQLite3 to store:

- Story details (ID, title, URL, score, author, timestamp)
- Article content in markdown format
- Content fetching status for each story (0 = not fetched, 1 = success, 2 = error, 3 = unavailable)
- Error details (error type, message, status code)
- Content fetch attempt timestamps
- Metadata such as the last time the program was run

The database file (`hn_stories.db`) is created in the same directory as the script.