# Hacker News Poller

A Python application that polls Hacker News for stories from the past 24 hours with a score of 10 or higher, displaying them in the console. Story data is stored in a SQLite database for tracking and filtering purposes.

## Features

- Efficiently retrieves stories from Hacker News API using batching
- Tracks and updates story scores over time
- Filters stories by age (last 24 hours) and quality (score ≥ 10)
- Uses asynchronous requests for better performance
- Stores and updates story data in a local SQLite database
- Intelligently tracks last processed stories to minimize redundant fetching

## Requirements

- Python 3.12+
- `uv` Python package manager
- Dependencies (automatically installed):
  - requests: HTTP library for API calls
  - aiohttp: Asynchronous HTTP client
  - asyncio: Asynchronous I/O library

## Installation

1. Clone this repository

2. Use the setup script (recommended):
   ```
   # Run the setup script
   ./setup.sh
   ```

   Or set up manually with `uv` (the recommended package manager for this project):
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

   > **Important**: This project uses `uv` for Python package management rather than pip. Always use `uv pip` commands for installing packages to ensure proper dependency resolution.

## Usage

To poll for stories from the past 24 hours with scores ≥ 10:

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

- `--hours N`: Specify how many hours back to look for stories (default: 24)
- `--min-score N`: Specify minimum score threshold for displaying stories (default: 10)
- `--batch-size N`: Specify how many stories to process in each batch (default: 100)
- `--max-batches N`: Specify maximum number of batches to process (default: 10)

## How It Works

1. The program fetches new stories in batches until it either:
   - Reaches a story older than the 24-hour cutoff
   - Encounters the last oldest ID from a previous run
   - Processes the maximum number of allowed batches

2. For each story, it:
   - Adds new stories to the database
   - Updates scores for existing stories in the database
   - Tracks the oldest story ID for optimization in future runs

3. After processing all stories, it queries the database for:
   - Stories from the past 24 hours (configurable)
   - With scores greater than or equal to 10 (configurable)

4. These high-quality stories are displayed in the console, sorted by score

## Database

The application uses SQLite3 to store:

- Story details (ID, title, URL, score, author, timestamp, last updated time)
- Metadata such as:
  - Last poll time
  - Last oldest ID processed (for optimization)

The database file (`hn_stories.db`) is created in the same directory as the script.

## Performance Considerations

- The application uses async/await for concurrent API requests
- It implements a throttling mechanism to avoid API rate limits
- Batch processing allows efficient handling of large datasets
- Tracking the oldest ID processed minimizes redundant processing
- The application is designed to be run periodically (e.g., hourly)