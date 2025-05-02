# Hacker News Poller

A high-performance Python application that polls Hacker News for high-quality stories, displaying them in the console. The application can fetch from top, best, or new story feeds and filter by time and score. Story data is stored in a SQLite database for tracking and filtering purposes.

## Features

- Efficiently retrieves high-quality stories directly from Hacker News API
- Choose between top, best, or new story feeds
- Processes up to 500 stories in a single request with asynchronous processing
- Tracks and updates story scores over time
- Filters stories by age (default 24 hours) and quality (default score ≥ 30)
- Uses asynchronous requests with high concurrency for optimal performance
- Stores and updates story data in a local SQLite database
- Intelligently tracks processed stories to minimize redundant fetching
- Claude AI-powered personalized filtering based on your interests
- Smart scoring system that combines HN score and relevance score with configurable weights

## Requirements

- Python 3.12+
- `uv` Python package manager
- Anthropic API key (only for Claude filtering)
- Dependencies (automatically installed):
  - requests: HTTP library for API calls
  - aiohttp: Asynchronous HTTP client
  - asyncio: Asynchronous I/O library
  - anthropic: Claude AI API client (for personalized filtering)

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

The application has three main commands:

- `fetch`: Fetch stories from Hacker News and store in the database
- `score`: Calculate relevance scores for unscored stories using Claude AI
- `show`: Display stories meeting criteria (default command if none specified)

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

The program operates in three distinct modes, each with its own responsibilities:

### 1. Data Collection (Fetch)

The `fetch` command is responsible for:
- Getting story data from the Hacker News API
- Filtering by timeframe and score
- Saving new stories to the database
- Updating existing stories
- Optimizing future runs by tracking metadata

### 2. Relevance Scoring (Score)

The `score` command:
- Retrieves unscored stories from the database
- Sends each story to Claude AI for relevance evaluation
- Calculates a relevance score (0-100) indicating how well it matches your interests
- Stores the relevance scores in the database
- Processes in configurable batch sizes to manage API usage

### 3. Display (Show)

The `show` command:
- Queries the database for stories meeting criteria
- Filters by both HN score and relevance score
- Calculates a combined score based on both HN score and relevance score
- Normalizes HN scores with logarithmic scaling to reduce the impact of extremely high scores
- Allows adjusting weight between HN score and relevance score with `--hn-weight`
- Sorts results by combined score for optimal story ranking
- Displays formatted output in the console with all scores

## Database

The application uses SQLite3 to store:

- Story details including:
  - ID, title, URL, score, author, timestamp, last updated time
  - Relevance score (0-100, indicating how relevant the story is to user interests)
- Metadata such as:
  - Last poll time
  - Last oldest ID processed (for optimization)

The database file (`hn_stories.db`) is created in the same directory as the script.

See [Database Schema](docs/db_schema.md) for more details on the database structure.

## Performance Considerations

- Direct fetching of pre-filtered story lists (top/best) for optimal performance
- High-concurrency asynchronous processing for simultaneous story retrieval
- Single pass processing eliminates the need for batch processing
- Rate limiting and error handling for API reliability
- Tracking the oldest ID processed minimizes redundant processing
- Early filtering reduces database operations and memory usage
- Optimized for fast execution even with large numbers of stories
- The application is designed to be run periodically (e.g., hourly or daily)

## Personalized Relevance Scoring

When using the scoring feature, the application leverages Claude AI to calculate relevance scores for stories:

- Current interest categories:
  - Programming and software development
  - AI, machine learning, and LLMs
  - Linux, Emacs, NixOS
  - Computer science theory and algorithms
  - Cybersecurity, hacking techniques, and security vulnerabilities
  - Science fiction concepts and technology
  - Hardware hacking and electronics
  - Systems programming and low-level computing
  - Novel computing paradigms and research
  - Tech history and vintage computing
  - Mathematics and computational theory
  - Cool toys and gadgets
  - Climate Change and Mitigation

To customize these interests, edit the system prompt in `src/classifier.py`.

Each story receives a relevance score from 0-100 indicating how well it matches your interests:
- 0-25: Not relevant
- 26-50: Slightly relevant
- 51-75: Moderately relevant
- 76-100: Highly relevant

**Key advantages of the relevance score system:**
- Scores are persisted in the database, minimizing redundant API calls
- The Anthropic API is only called for stories without existing scores
- Users can adjust the relevance threshold to be more or less selective
- Scores are displayed with each story, providing insight into the filtering system
- Domain-based caching reduces API calls for common websites
- Batch processing with asynchronous requests for performance

The optimized relevance scoring system employs several strategies to minimize API usage:
1. **Database Persistence**: Scores are stored in the database so they only need to be calculated once
2. **Domain Caching**: Common domains are cached to avoid redundant scoring
3. **Batch Processing**: Processes multiple stories concurrently for efficiency
4. **Separation of Concerns**: Clear separation between fetching, scoring, and displaying

Claude analyzes story titles and domains to determine relevance scores. This provides a personalized feed of only the stories you're likely to find interesting, while efficiently using the AI service.

## Typical Workflow

A typical workflow might look like this:

1. **Initial Setup**:
   ```bash
   # Set up your API key (for relevance scoring)
   export ANTHROPIC_API_KEY=your_api_key_here
   ```

2. **Regular Usage**:
   ```bash
   # 1. Fetch new stories from Hacker News
   hn-poll fetch
   
   # 2. Calculate relevance scores for new stories
   hn-poll score
   
   # 3. Show high-quality, relevant stories
   hn-poll show
   ```

3. **Custom Filtering**:
   ```bash
   # Show stories with custom thresholds
   hn-poll show --min-score 20 --min-relevance 60
   
   # Adjust the weighting between HN score and relevance score
   hn-poll show --hn-weight 0.5  # Equal weighting between HN and relevance
   hn-poll show --hn-weight 0.3  # Favor relevance score more heavily
   hn-poll show --hn-weight 0.9  # Favor HN score more heavily
   ```

This separation of concerns allows for more efficient API usage and clearer operation.