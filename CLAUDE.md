# Hackernews Poller Project - Claude Notes

## Project Overview

This project is a Python application that polls the Hacker News API for stories from the past 24 hours with a score of 10 or higher, displaying them in the console. The application stores and updates story data in a SQLite database for tracking and filtering purposes.

## Technologies Used

- **Python 3.12**: Core programming language
- **uv**: Modern Python package manager for dependency management
- **requests**: For making HTTP requests to the Hacker News API
- **sqlite3**: Python's built-in SQLite database interface
- **argparse**: For command-line argument parsing
- **aiohttp**: For asynchronous HTTP requests
- **asyncio**: For asynchronous programming

## Project Structure

- `src/`: Main source code directory
  - `api.py`: Contains functions for interacting with the Hacker News API, including batch fetching and async support
  - `db.py`: Database operations (initialization, queries, updates, score tracking)
  - `main.py`: Main program logic and command-line interface
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
hn-poll --hours 48 --min-score 5

# Or run directly
python src/main.py
```

## How It Works

1. **Database Initialization**: When first run, the application creates a SQLite database with tables for stories and metadata. See [Database Schema](docs/db_schema.md) for details.

2. **Efficient API Integration**: The application uses the Hacker News Firebase API to fetch stories in batches, stopping when it either:
   - Reaches a story older than the specified timeframe (default: 24 hours)
   - Encounters the oldest ID from a previous run
   - Processes the maximum number of allowed batches

3. **Story Management**: 
   - New stories are added to the database
   - Existing stories have their scores updated
   - The application tracks the oldest story ID processed to optimize future runs

4. **Quality Filtering**: After processing all stories, the application queries the database for:
   - Stories from the past 24 hours (configurable)
   - With scores greater than or equal to 10 (configurable)

5. **Console Output**: High-quality stories are formatted and displayed to the console, sorted by score.

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

- The application uses async/await for concurrent API requests
- It implements a throttling mechanism to avoid API rate limits
- Batch processing allows efficient handling of large datasets
- Tracking the oldest ID processed minimizes redundant processing 
- The application is designed to be run periodically (e.g., hourly)

## Future Enhancements

Potential improvements to consider:
- Add colorful console output using a library like `rich` or `colorama`
- Create a simple web dashboard using Flask or FastAPI
- Add export functionality to different formats (JSON, CSV)
- Implement more advanced filtering options (by type, domain, keywords)
- Add user configuration file for persistent settings
- Add a full test suite with pytest