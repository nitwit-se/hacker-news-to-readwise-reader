# Hacker News Poller Project TODOs

## Project Setup ✅
- [x] Create project structure with uv package management
- [x] Install required packages (requests, sqlite3)
- [x] Set up basic project structure

## Database Implementation ✅
- [x] Design SQLite schema for storing stories
- [x] Create database initialization script
- [x] Implement functions for story insertion/retrieval
- [x] Add functionality to track last poll timestamp
- [x] Add score update capability for existing stories
- [x] Add timestamp-based filtering for stories
- [x] Implement tracking of oldest processed ID

## API Integration ✅
- [x] Implement Firebase API client for Hacker News
- [x] Create functions to fetch new stories
- [x] Add item detail retrieval functionality
- [x] Implement error handling for API requests
- [x] Add batch processing and pagination
- [x] Implement async/concurrent requests

## Core Functionality ✅
- [x] Create logic to determine new stories since last poll
- [x] Implement story processing and filtering
- [x] Develop console output formatting
- [x] Add main program execution flow
- [x] Implement quality filtering (score ≥ 10)
- [x] Add timeframe-based filtering (last 24 hours)
- [x] Add optimization for recurring polls

## Testing & Documentation ✅
- [x] Test with real Hacker News data
- [x] Add comprehensive error handling
- [x] Create README with usage instructions
- [x] Document code with docstrings
- [x] Update documentation to reflect new approach

## Optional Enhancements (Future Work)
- [x] Add story filtering options (by score, timeframe)
- [x] Implement command-line arguments
- [x] Optimize performance with direct source selection (top/best/new)
- [x] Add Claude AI integration for interest-based filtering
- [ ] Create simple web dashboard
- [ ] Add export functionality
- [ ] Add colorful console output
- [ ] Implement full test suite
- [ ] Add user configuration file
- [ ] Add more advanced filtering (by type, domain, keywords)
- [ ] Improve Claude AI integration with response caching
- [ ] Add ability to customize interest categories via config file

## Project Management
- [x] Update TODO.md with completed items
- [x] Create CLAUDE.md with project information
- [x] Initialize git repository