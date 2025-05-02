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

## Architecture Improvements ✅
- [x] Refactor command structure to use subcommands
- [x] Separate concerns into fetch, score, and show operations
- [x] Implement consistent relevance score handling
- [x] Improve filtering and sorting of stories by relevance
- [x] Update documentation to reflect new architecture

## Testing & Documentation ✅
- [x] Test with real Hacker News data
- [x] Add comprehensive error handling
- [x] Create README with usage instructions
- [x] Document code with docstrings
- [x] Update documentation to reflect new approach
- [x] Test all operational modes to ensure they work correctly

## Optional Enhancements (Future Work)
- [x] Add story filtering options (by score, timeframe)
- [x] Implement command-line arguments
- [x] Optimize performance with direct source selection (top/best/new)
- [x] Add Claude AI integration for interest-based filtering
- [x] Implement relevance score storage for Claude AI integration
- [x] Add database persistence for relevance scores
- [x] Improve Claude AI integration with response caching via database
- [x] Optimize Anthropic API usage with domain-based caching
- [x] Add asynchronous batch processing for relevance scoring
- [x] Create background worker script for independent story scoring
- [x] Add flexible scoring modes (scored-only, background-score)
- [ ] Create simple web dashboard
- [ ] Add export functionality
- [ ] Add colorful console output
- [ ] Implement full test suite
- [ ] Add user configuration file
- [ ] Add more advanced filtering (by type, domain, keywords)
- [ ] Add ability to customize interest categories via config file
- [ ] Implement automatic scheduled scoring with cron/systemd

## Project Management
- [x] Update TODO.md with completed items
- [x] Create CLAUDE.md with project information
- [x] Initialize git repository