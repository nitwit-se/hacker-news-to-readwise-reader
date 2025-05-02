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

1. **Database Initialization**: When first run, the application creates a SQLite database with tables for stories and metadata.

2. **API Integration**: The application uses the Hacker News Firebase API to fetch the latest stories.

3. **Story Tracking**: Story IDs are compared with the database to determine which stories are new since the last run.

4. **Content Fetching**: For selected stories, the application fetches content from the story URLs and converts it to markdown format. Advanced features include:
   - Prioritization of new stories for content fetching
   - Retry mechanism with exponential backoff for transient errors
   - Special handling for sites that block content fetching (e.g., Twitter)
   - Error categorization and storage in the database
   - Comprehensive summary generation for display

5. **Console Output**: New stories are formatted and displayed to the console, sorted by score, with content summaries where available.

## Development Notes

### Python Packaging

This project uses the modern Python packaging approach with `pyproject.toml` and the `uv` package manager, which offers:
- Faster dependency resolution
- Better compatibility with modern Python packaging standards
- Consistent environment creation

### Shell Compatibility

The setup script and documentation include support for both:
- Bash/Zsh shells
- Fish shell

### Database Schema

```sql
CREATE TABLE stories (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    score INTEGER,
    by TEXT NOT NULL,
    time INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT,
    content_fetched INTEGER DEFAULT 0,
    error_type TEXT,
    error_message TEXT,
    error_status INTEGER,
    last_fetch_attempt TEXT
)

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
```

The `content_fetched` field uses the following status codes:
- `0`: Content has not been fetched yet
- `1`: Content was successfully fetched
- `2`: Content fetch was attempted but failed with an error
- `3`: Content is known to be unavailable (e.g., Twitter URLs)

## Content Extraction Strategy

The project uses a sophisticated approach to extract meaningful content from web pages while excluding navigation, ads, and other non-content elements:

### 1. Content Identification Heuristics

The content extraction process follows a multi-stage approach:

1. **Main Content Container Identification**:
   - Searches for common content container elements using selectors like `article`, `main`, `.content`, `#content`
   - Falls back to finding the div with the most text content if no identifiable container exists
   - Requires a minimum text length (200 chars) to qualify as main content

2. **Non-Content Element Removal**:
   - Removes script, style, nav, header, footer, and aside elements
   - Filters out elements with class names matching navigation patterns
   - Removes social media buttons and copyright notices

3. **Content Cleaning**:
   - Removes reference-style links that often appear at the end of articles
   - Filters out consecutive short lines that are likely menu items
   - Preserves headings and meaningful paragraph text
   - Cleans up excessive blank lines

4. **Summary Generation**:
   - Extracts first few paragraphs to create a meaningful summary
   - Removes markdown formatting from the summary for clean display
   - Truncates to desired length while preserving sentence structure

This approach balances effectiveness with simplicity by using existing dependencies (BeautifulSoup and html2text) without adding additional requirements. It provides high-quality content extraction without the overhead of more complex machine learning-based solutions.

### Benefits of This Approach

- **Progressive Enhancement**: Builds on existing functionality rather than replacing it
- **Minimal Dependencies**: Leverages already-required libraries
- **Targeted Extraction**: Focuses specifically on article content
- **Maintainable Code**: Clear separation of concerns with distinct processing stages
- **Adaptable**: Works with a wide variety of web page structures

## Package Management with uv

This project uses `uv` for Python package management rather than pip. Key benefits include:

- **Performance**: Much faster dependency resolution and installation 
- **Reproducibility**: Consistent environment creation across different systems
- **Compatibility**: Better alignment with modern Python packaging standards (PEP 621)

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
- Add export functionality to CSV or JSON formats
- Implement concurrent API requests for faster story fetching
- Add a full test suite with pytest
- Further enhance content extraction with more advanced NLP techniques
- Add options to save favorite stories for later reading
- Create a notification system for high-scoring stories
- Add support for comments and discussion threads