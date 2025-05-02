# Hackernews Poller Project - Claude Notes

## Project Overview

This project is a Python application that polls the Hacker News API for new stories and displays them in the console. The application stores story data in a SQLite database to track which stories are new since the last run.

## Technologies Used

- **Python 3.12**: Core programming language
- **uv**: Modern Python package manager for dependency management
- **requests**: For making HTTP requests to the Hacker News API
- **sqlite3**: Python's built-in SQLite database interface
- **argparse**: For command-line argument parsing
- **html2text**: For converting HTML to markdown
- **BeautifulSoup**: For parsing HTML content

## Project Structure

- `src/`: Main source code directory
  - `api.py`: Contains functions for interacting with the Hacker News API
  - `db.py`: Database operations (initialization, queries, updates)
  - `main.py`: Main program logic and command-line interface
  - `content.py`: Content fetching and processing functionality
- `docs/`: Documentation files
  - `db_schema.md`: Database schema details
  - `content_extraction.md`: Content extraction strategy details
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

# Run with custom limit
hn-poll --limit 50

# Or run directly
python src/main.py
```

## How It Works

1. **Database Initialization**: When first run, the application creates a SQLite database with tables for stories and metadata. See [Database Schema](docs/db_schema.md) for details.

2. **API Integration**: The application uses the Hacker News Firebase API to fetch the latest stories.

3. **Story Tracking**: Story IDs are compared with the database to determine which stories are new since the last run.

4. **Content Fetching**: For selected stories, the application fetches content from the story URLs and converts it to markdown format. Features include:
   - Prioritization of new stories for content fetching
   - Retry mechanism with exponential backoff for transient errors
   - Special handling for sites that block content fetching
   - See [Content Extraction Strategy](docs/content_extraction.md) for full details

5. **Console Output**: New stories are formatted and displayed to the console, sorted by score, with content summaries where available.

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

## Future Enhancements

Potential improvements to consider:
- Add colorful console output using a library like `rich` or `colorama`
- Implement story filtering by type, score, or keywords
- Create a simple web dashboard using Flask or FastAPI
- Implement concurrent API requests for faster story fetching
- Add a full test suite with pytest