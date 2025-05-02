# Hacker News Poller

A high-performance Python application that polls Hacker News for high-quality stories, displaying them in the console. The application can fetch from top, best, or new story feeds and filter by time and score. Story data is stored in a SQLite database for tracking and filtering purposes.

## Features

- Efficiently retrieves high-quality stories directly from Hacker News API
- Choose between top, best, or new story feeds
- Processes up to 500 stories in a single request with asynchronous processing
- Tracks and updates story scores over time
- Filters stories by age (default 24 hours) and quality (default score ≥ 10)
- Uses asynchronous requests with high concurrency for optimal performance
- Stores and updates story data in a local SQLite database
- Intelligently tracks processed stories to minimize redundant fetching
- Optional Claude AI-powered personalized filtering based on your interests

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
- `--source [top|best|new]`: Select which Hacker News feed to use (default: top)
- `--limit N`: Maximum number of stories to fetch from source (default: 500)
- `--claude`: Use Claude AI to calculate relevance scores (requires ANTHROPIC_API_KEY)
- `--min-relevance N`: Set minimum relevance score threshold for Claude filtering (default: 75)
- `--scored-only`: Only show stories that already have a relevance score (no new API calls)
- `--background-score`: Use background scoring process instead of inline scoring

For Claude AI relevance scoring and filtering:
```bash
# Set your Anthropic API key
export ANTHROPIC_API_KEY=your_api_key_here

# Run with Claude relevance scoring
hn-poll --claude

# Run with Claude relevance scoring and custom threshold
hn-poll --claude --min-relevance 60

# Only show stories that already have scores (no API calls)
hn-poll --claude --scored-only

# Show all stories but suggest running background scorer for unscored stories
hn-poll --claude --background-score
```

For background processing of relevance scores:
```bash
# Run the background scorer to process ALL unscored stories in the database
python src/background_scorer.py

# Process only stories from the past 72 hours
python src/background_scorer.py --hours 72

# Only score stories with at least 5 points
python src/background_scorer.py --min-score 5

# Customize background scoring further
python src/background_scorer.py --batch-size 20 --max-stories 100
```

## How It Works

1. The program fetches stories from the selected source (top, best, or new):
   - Gets up to 500 pre-curated story IDs in a single API call
   - Efficiently processes these stories asynchronously with high concurrency
   - Applies time and score filters directly during processing

2. For each story, it:
   - Filters by timeframe (default: 24 hours) and score (default: ≥ 10)
   - Adds new stories to the database
   - Updates scores for existing stories
   - Tracks the oldest ID for optimization

3. If Claude relevance scoring is enabled, the application:
   - Sends each story title and URL to Claude AI for stories without existing scores
   - Calculates a relevance score (0-100) indicating how well it matches your interests
   - Stores the relevance scores in the database for future use
   - Filters stories based on the minimum relevance threshold (default: 75)
   - Displays relevance scores alongside other story information

4. The filtered, high-quality stories are:
   - Sorted by score in descending order
   - Displayed directly in the console
   - Stored in the database for future reference

5. The program tracks metadata to optimize future runs:
   - Last poll time
   - Oldest story ID processed

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

When using the `--claude` flag, the application leverages Claude AI to calculate relevance scores for stories:

- Current interest categories:
  - Technology & Tools: Emacs, Linux, NixOS, MacOS, Apple hardware, e-book readers
  - Programming & Computer Science: Python, Julia, Lisp, functional programming, logic programming
  - Security & Hacking: InfoSec, cybersecurity, ethical hacking, cracking
  - Projects & Creativity: DIY/home projects, creative coding, hardware hacking
  - Science & Research: AI, machine learning, climate change, scientific computing
  - Books & Reading: Technical books, e-book technology, digital reading

To customize these interests, edit the system prompt in `src/classifier.py`.

Each story receives a relevance score from 0-100 indicating how well it matches your interests:
- 0-25: Not relevant
- 26-50: Slightly relevant
- 51-75: Moderately relevant
- 76-100: Highly relevant

**Key advantages of the relevance score system:**
- Scores are persisted in the database, minimizing redundant API calls
- The Anthropic API is only called for new stories without existing scores
- Users can adjust the relevance threshold to be more or less selective
- Scores are displayed with each story, providing insight into the filtering system
- Domain-based caching reduces API calls for common websites
- Batch processing with asynchronous requests for performance
- Background scoring option to separate API calls from main application
- "Scored-only" mode to use the system without making any API calls

The optimized relevance scoring system employs several strategies to minimize API usage:
1. **Database Persistence**: Scores are stored in the database so they only need to be calculated once
2. **Domain Caching**: Common domains are cached to avoid redundant scoring
3. **Batch Processing**: Processes multiple stories concurrently for efficiency
4. **Background Processing**: Optional separation of API calls into a background process
5. **Flexible Modes**: Choose between inline scoring, background scoring, or scored-only modes

Claude analyzes story titles and domains to determine relevance scores. This provides a personalized feed of only the stories you're likely to find interesting, while efficiently using the AI service.