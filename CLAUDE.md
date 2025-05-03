# Hackernews Poller Project - Claude Notes

## Project Overview

This project is a high-performance Python application that polls the Hacker News API for high-quality stories, displaying them in the console. The application can fetch from top, best, or new story feeds, applying time and score filters. All story data is stored in a SQLite database for tracking and filtering purposes.

## Technologies Used

- **Python 3.12**: Core programming language with type hints
- **uv**: Modern Python package manager for dependency management
- **requests**: For making HTTP requests to the Hacker News API
- **sqlite3**: Python's built-in SQLite database interface
- **argparse**: For command-line argument parsing
- **aiohttp**: For asynchronous HTTP requests
- **asyncio**: For asynchronous programming
- **anthropic**: Python client for the Anthropic Claude API
- **typing**: For static type annotations throughout the codebase
- **pytest**: For comprehensive unit and integration testing

## Project Structure

- `src/`: Main source code directory
  - `api.py`: Contains functions for interacting with the Hacker News API, including batch fetching and async support
  - `db.py`: Database operations (initialization, queries, updates, score tracking)
  - `main.py`: Main program logic and command-line interface
  - `classifier.py`: Claude AI integration for interest-based filtering
- `tests/`: Test suite
  - `unit/`: Unit tests for individual modules
  - `integration/`: Integration tests for component interaction
  - `fixtures/`: Shared test fixtures and utilities
- `docs/`: Documentation files
  - `db_schema.md`: Database schema details
- `pyproject.toml`: Project configuration and dependencies
- `pytest.ini`: Configuration for the pytest testing framework
- `setup.sh`: Shell script to set up the development environment
- `README.md`: User documentation
- `TODO.md`: Development task tracking

## Commands to Run

### Setup
```bash
# Create environment and install dependencies
./setup.sh
```

### Run
```bash
# Run the application
uv run python src/main.py

# Run with custom settings
uv run python -m src.main --hours 48 --min-score 5 --source best

# Available sources: top, best, new
uv run python -m src.main --source best

# Use Claude AI for interest-based filtering
export ANTHROPIC_API_KEY=your_api_key_here
uv run python -m src.main --claude
```

### Testing
```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run all tests
uv run pytest

# Run tests with coverage report
uv run pytest --cov=src

# Run specific test categories
uv run pytest -m unit              # Only unit tests
uv run pytest -m integration       # Only integration tests
uv run pytest -m "unit and db"     # Only database unit tests

# Run tests verbosely
uv run pytest -v

# Run a specific test file
uv run pytest tests/unit/test_api.py
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
   - Quality (default: stories with scores ≥ 30)
   - Source selection (top, best, or new stories)

5. **Interest-Based Filtering (Optional)**: When using the `--claude` flag:
   - Each story is analyzed by Claude AI against personalized interest categories
   - Interest categories include technology, programming, security, DIY projects, and more
   - Only stories matching user interests are kept in the final output

6. **Smart Scoring and Sorting**: The application uses a weighted scoring system:
   - Combines HN score and relevance score using a configurable weighted formula
   - Normalizes HN scores using a logarithmic scale to reduce the impact of extremely high scores
   - Allows adjustment of weighting between HN score and relevance score via `--hn-weight`
   - Scores are combined on a scale of 0-100 for consistent comparison

7. **Console Output**: High-quality stories are formatted and displayed to the console, sorted by combined score.

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

### Type Hints Policy

All code in this project uses Python type hints to improve code quality and maintainability:

- **Required for all functions**: Every function must include parameter and return type annotations
- **Type consistency**: Use consistent type annotations across the codebase 
- **Common types used**:
  - `List[T]`, `Dict[K, V]`, `Tuple[T, ...]` for container types
  - `Optional[T]` for values that might be None
  - `Union[T1, T2, ...]` for values that could be multiple types
  - `Any` only when absolutely necessary

- **Benefits**:
  - Enhanced code readability and self-documentation
  - Better IDE support for autocompletion and error detection
  - Catches potential type-related issues early
  - Facilitates static analysis tools like mypy

- **Style guidance**:
  - Always add return type annotations, including `-> None` for functions with no return value
  - Specify collection types with their element types (e.g., `List[Dict[str, Any]]`, not just `list`)
  - Use descriptive type aliases for complex types when appropriate

All new code contributions must include proper type annotations following these guidelines.

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
- Improve test coverage and add more edge case tests
- Improve Claude AI integration with response caching
- Add ability to customize interest categories via configuration file
- Create visualization of story score trends over time