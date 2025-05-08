# Hacker News Poller

A Python application that polls Hacker News for stories based on your interests. It fetches stories from top, best, or new feeds, filters them by time and score, and can optionally use Claude AI to rank story relevance to your personal interests. The application maintains state in a SQLite database to track stories, avoid duplicates, and preserve relevance scores between runs. Stories can be displayed in the console or synced to Readwise Reader.

## Features

- Retrieves stories from Hacker News API (top, best, or new feeds)
- Filters stories by age and score
- Stores story data in a local SQLite database
- Optional Claude AI integration for personalized filtering based on your interests
- Combines HN score and relevance score with configurable weights
- Integration with Readwise Reader for saving filtered stories

## Requirements

- Python 3.12+
- `uv` Python package manager
- Anthropic API key (only for Claude filtering)
- Readwise Reader API key (only for syncing to Readwise)
- Dependencies (automatically installed):
  - requests: HTTP library for API calls
  - aiohttp: Asynchronous HTTP client
  - asyncio: Asynchronous I/O library
  - anthropic: Claude AI API client (for personalized filtering)
  - typing: Python's static type annotations
  - backoff: Retry handling for API requests

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

The application has five main commands:

- `fetch`: Fetch stories from Hacker News and store in the database
- `score`: Calculate relevance scores for unscored stories using Claude AI
- `show`: Display stories meeting criteria (default command if none specified)
- `sync`: Sync high-quality stories to Readwise Reader
- `clean`: Clean the database of non-existent stories (remove ghost stories)

### Basic Usage

```bash
# Activate the environment if not already activated
# For bash/zsh
source .venv/bin/activate

# For fish shell
source .venv/bin/activate.fish

# Run using the installed command (defaults to 'show' command)
hn-poll

# Or run directly
python src/main.py
```

### Fetch Command: Get stories from Hacker News

```bash
# Fetch top stories with default settings (24 hours, min score 30)
hn-poll fetch

# Fetch stories with custom parameters
hn-poll fetch --hours 48 --min-score 20 --source new --limit 1000
```

Fetch Options:
- `--hours N`: Specify how many hours back to look for stories (default: 24)
- `--min-score N`: Specify minimum score threshold for stories (default: 30)
- `--source [top|best|new]`: Select which Hacker News feed to use (default: top)
- `--limit N`: Maximum number of stories to fetch from source (default: 500)

### Score Command: Calculate relevance scores with Claude AI

```bash
# Set your Anthropic API key (required for scoring)
export ANTHROPIC_API_KEY=your_api_key_here

# Score all unscored stories with default settings
hn-poll score

# Score with custom parameters
hn-poll score --hours 48 --min-score 20 --batch-size 20
```

Score Options:
- `--hours N`: Specify how many hours back to look for unscored stories (default: 24)
- `--min-score N`: Only score stories with at least this HN score (default: 30)
- `--batch-size N`: Number of stories to process in each batch (default: 10)
- `--extract-content`: Extract and analyze article content for more accurate scoring
- `--story-prompt PATH`: Path to custom story relevance prompt template file
- `--domain-prompt PATH`: [DEPRECATED] This option is deprecated and will be ignored

### Show Command: Display filtered stories

```bash
# Show stories meeting default criteria (HN score ≥ 30, relevance score ≥ 75)
hn-poll show

# Or just (as 'show' is the default command)
hn-poll

# Show with custom parameters
hn-poll show --hours 48 --min-score 20 --min-relevance 60
```

Show Options:
- `--hours N`: Specify how many hours back to look for stories (default: 24)
- `--min-score N`: Minimum HN score threshold (default: 30)
- `--min-relevance N`: Minimum relevance score threshold (default: 75)
- `--hn-weight N`: Weight to apply to HN score in combined scoring (0.0-1.0, default: 0.7)

## How It Works

The program operates in three main modes:

### 1. Data Collection (Fetch)

The `fetch` command gets story data from the Hacker News API, filters by timeframe and score, and saves stories to the database.

### 2. Relevance Scoring (Score)

The `score` command sends unscored stories to Claude AI for relevance evaluation, calculating a score (0-100) that indicates how well each story matches your interests.

### 3. Display (Show)

The `show` command queries the database for stories meeting your criteria, filters by both HN score and relevance score, and displays results sorted by a combined score.

## Database

The application uses SQLite3 to store story details and metadata. The database file (`hn_stories.db`) is created in the same directory as the script.

See [Database Schema](docs/db_schema.md) for more details.

## Implementation Notes

- Uses asynchronous processing for story retrieval
- Implements rate limiting and error handling for API reliability
- Tracks previously processed stories to avoid redundant operations
- Applies filtering to reduce database operations
- Designed to be run periodically (e.g., hourly or daily)

## Type Hints

This project uses Python's type hint system throughout the codebase. Contributors should maintain type hints with all new code or modifications.

## Testing

This project uses pytest for testing. The test suite includes:

- Unit tests for individual components
- Integration tests for component interactions
- Fixtures for database and API mocking
- Test coverage reporting

### Running Tests

```bash
# Activate your virtual environment
source .venv/bin/activate  # or source .venv/bin/activate.fish for fish shell

# Install development dependencies if not already installed
uv pip install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage report
pytest --cov=src

# Run specific test categories
pytest -m unit              # Only unit tests
pytest -m integration       # Only integration tests
pytest -m "unit and db"     # Only database unit tests
pytest -m "unit and api"    # Only API unit tests

# Run tests verbosely
pytest -v

# Run a specific test file
pytest tests/unit/test_api.py
```

### Test Structure

- `tests/unit/`: Unit tests for individual modules
- `tests/integration/`: Integration tests across modules
- `tests/fixtures/`: Shared test fixtures and utilities

When adding new features, please include appropriate tests to maintain code quality.

## Personalized Relevance Scoring

The application can use Claude AI to calculate relevance scores for stories based on how well they match your interests.

- Default interest categories are defined in `prompts/story_relevance.txt`
- Scores range from 0-100, where higher scores indicate better matches to your interests
- You can customize interests by editing the template file or creating your own

### Customizing Prompt Template

You can tailor the interest categories to your preferences:

1. Edit the default template in `prompts/story_relevance.txt`
2. Or use a custom template:
   ```bash
   hn-poll score --story-prompt /path/to/your/template.txt
   ```
3. You can also set this path using an environment variable:
   ```bash
   export HN_STORY_PROMPT_FILE=/path/to/your/template.txt
   ```

The scoring system only calls the Anthropic API for stories without existing scores and stores results in the database to minimize redundant API calls.

### Sync Command: Save stories to Readwise Reader

```bash
# Set your Readwise Reader API key (required for syncing)
export READWISE_API_KEY=your_api_key_here

# Sync stories with default settings (24 hours, HN score ≥ 30, relevance score ≥ 75)
hn-poll sync

# Sync with custom parameters
hn-poll sync --hours 48 --min-score 20 --min-relevance 60 --batch-size 5
```

Sync Options:
- `--hours N`: Specify how many hours back to look for stories (default: 24)
- `--min-score N`: Minimum HN score threshold (default: 30)
- `--min-relevance N`: Minimum relevance score threshold (default: 75)
- `--batch-size N`: Number of stories to process in each batch (default: 10)
- `--max-stories N`: Maximum number of stories to sync (useful for testing)
- `--no-relevance-filter`: Disable relevance filtering (not recommended)

### Clean Command: Remove non-existent stories

Over time, the database might accumulate references to stories that no longer exist on Hacker News. The `clean` command helps remove these "ghost" stories:

```bash
# Clean the database with default settings
hn-poll clean

# Clean with custom parameters
hn-poll clean --batch-size 50 --max-batches 20
```

Clean Options:
- `--batch-size N`: Number of stories to check in each batch (default: 100)
- `--max-batches N`: Maximum number of batches to process (default: 10)

## Typical Workflow

A typical workflow might look like this:

1. **Initial Setup**:
   ```bash
   # Set up your API keys
   export ANTHROPIC_API_KEY=your_api_key_here  # For relevance scoring
   export READWISE_API_KEY=your_api_key_here   # For Readwise syncing
   ```

2. **Regular Usage**:
   ```bash
   # 1. Fetch new stories from Hacker News
   hn-poll fetch
   
   # 2. Calculate relevance scores for new stories
   hn-poll score
   
   # 3. Show high-quality, relevant stories
   hn-poll show
   
   # 4. Optionally, sync stories to Readwise Reader
   hn-poll sync
   ```

3. **Custom Filtering**:
   ```bash
   # Show stories with custom thresholds
   hn-poll show --min-score 20 --min-relevance 60
   
   # Adjust the weighting between HN score and relevance score
   hn-poll show --hn-weight 0.5  # Equal weighting between HN and relevance
   hn-poll show --hn-weight 0.3  # Favor relevance score more heavily
   hn-poll show --hn-weight 0.9  # Favor HN score more heavily
   
   # Sync stories with custom thresholds
   hn-poll sync --min-score 50 --min-relevance 80
   
   # Sync all stories regardless of relevance (not recommended)
   hn-poll sync --no-relevance-filter
   
   # Limit the number of stories to sync (useful for testing)
   hn-poll sync --max-stories 5
   ```

4. **Automated Workflow with Shell Script**:

   This project includes a convenient shell script that automates the entire fetch-score-sync workflow:

   ```bash
   # Run with default settings
   ./sync_stories.sh
   
   # Run with custom settings
   ./sync_stories.sh --hours 48 --min-score 20 --min-comments 10 --min-relevance 70 --max-stories 15 --source best
   
   # Run with database cleanup (removes non-existent stories)
   ./sync_stories.sh --cleanup
   
   # Run with custom cleanup settings
   ./sync_stories.sh --cleanup --batch-size 50 --max-batches 10
   ```

   Available options:
   - `--hours N`: Number of hours to look back (default: 24)
   - `--min-score N`: Minimum HN score threshold (default: 30)
   - `--min-comments N`: Minimum number of comments threshold (default: 20)
   - `--min-relevance N`: Minimum relevance score threshold (default: 75)
   - `--max-stories N`: Maximum number of stories to sync (default: 10)
   - `--source TYPE`: Source to fetch stories from (default: top, options: top, best, new)
   - `--cleanup`: Enable database cleanup to remove non-existent stories
   - `--batch-size N`: Number of stories to check in each cleanup batch (default: 50)
   - `--max-batches N`: Maximum number of batches for cleanup (default: 5)

The shell script automates the entire workflow with a single command.