# Hackernews Poller Project - Claude Notes

## Project Overview

This project is a high-performance Python application that polls the Hacker News API for high-quality stories, displaying them in the console. The application can fetch from top, best, or new story feeds, applying time and score filters. All story data is stored in a SQLite database for tracking and filtering purposes.

## Technologies Used

- **Python 3.12**: Core programming language
- **uv**: Modern Python package manager for dependency management
- **requests**: For making HTTP requests to the Hacker News API
- **sqlite3**: Python's built-in SQLite database interface
- **argparse**: For command-line argument parsing
- **aiohttp**: For asynchronous HTTP requests
- **asyncio**: For asynchronous programming
- **anthropic**: Python client for the Anthropic Claude API

## Project Structure

- `src/`: Main source code directory
  - `api.py`: Contains functions for interacting with the Hacker News API, including batch fetching and async support
  - `db.py`: Database operations (initialization, queries, updates, score tracking)
  - `main.py`: Main program logic and command-line interface
  - `classifier.py`: Claude AI integration for interest-based filtering
- `docs/`: Documentation files
  - `db_schema.md`: Database schema details
- `pyproject.toml`: Project configuration and dependencies
- `setup.sh`: Shell script to set up the development environment
- `README.md`: User documentation
- `TODO.md`: Development task tracking

## Commands to Run

### Setup
```bash
# Create environment and install dependencies
./setup.sh

# For bash/zsh shells
source .venv/bin/activate

# For fish shell
source .venv/bin/activate.fish
```

### Run
```bash
# Run via installed command
hn-poll

# Run with custom settings
hn-poll --hours 48 --min-score 5 --source best

# Available sources: top, best, new
hn-poll --source best

# Use Claude AI for interest-based filtering
export ANTHROPIC_API_KEY=your_api_key_here
hn-poll --claude

# Or run directly
python src/main.py
```

## How It Works

1. **Database Initialization**: When first run, the application creates a SQLite database with tables for stories and metadata. See [Database Schema](docs/db_schema.md) for details.

2. **Optimized API Integration**: The application uses the Hacker News Firebase API endpoints to efficiently fetch high-quality stories:
   - Directly fetches up to 500 pre-filtered stories from top, best, or new feeds
   - Processes stories asynchronously with high concurrency for optimal performance
   - Applies time and score filters during processing to minimize database operations

3. **Story Management**: 
   - New stories are added to the database
   - Existing stories have their scores updated
   - The application tracks the oldest story ID processed to optimize future runs

4. **Real-time Filtering**: The application filters stories by:
   - Time (default: stories from the past 24 hours)
   - Quality (default: stories with scores ≥ 10)
   - Source selection (top, best, or new stories)

5. **Interest-Based Filtering (Optional)**: When using the `--claude` flag:
   - Each story is analyzed by Claude AI against personalized interest categories
   - Interest categories include technology, programming, security, DIY projects, and more
   - Only stories matching user interests are kept in the final output

6. **Console Output**: High-quality stories are formatted and displayed to the console, sorted by score.

## Development Notes

### Python Packaging

This project uses the modern Python packaging approach with `pyproject.toml` and the `uv` package manager, which offers:
- Faster dependency resolution
- Better compatibility with modern Python packaging standards
- Consistent environment creation

### Package Management with uv

Always use `uv` commands for package management, for example:
```bash
# Install dependencies
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"

# Add a new dependency
uv pip install new-package-name
```

NEVER use pip directly in this project as it would bypass uv's dependency resolution.

## Performance Considerations

- Direct fetching of pre-filtered story lists (top/best) for optimal performance
- High-concurrency asynchronous processing for simultaneous story retrieval
- Single pass processing eliminates the need for batch processing
- Rate limiting and error handling for API reliability
- Tracking the oldest ID processed minimizes redundant processing
- Early filtering reduces database operations and memory usage
- Optimized for fast execution even with large numbers of stories
- The application is designed to be run periodically (e.g., hourly or daily)

## Future Enhancements

Potential improvements to consider:
- Add colorful console output using a library like `rich` or `colorama`
- Create a simple web dashboard using Flask or FastAPI
- Add export functionality to different formats (JSON, CSV)
- Implement more advanced filtering options (by type, domain, keywords)
- Add user configuration file for persistent settings
- Add a full test suite with pytest
- Improve Claude AI integration with response caching
- Add ability to customize interest categories via configuration file
- Create visualization of story score trends over time