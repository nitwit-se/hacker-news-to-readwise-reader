# Readwise Reader Integration

This document describes the integration with Readwise Reader in the Hacker News Poller project.

## Overview

The Readwise integration allows automatic syncing of high-quality Hacker News stories to your Readwise Reader account. Stories are filtered based on HN score and relevance score before being synced.

## API Details

The integration uses the Readwise Reader API v3:

- Base URL: `https://readwise.io/api/v3/`
- List Endpoint: `list/` - Used to fetch existing documents in your Readwise account
- Save Endpoint: `save/` - Used to add new documents to your Readwise account

Authentication is via token in the Authorization header:
```
Authorization: Token YOUR_API_KEY_HERE
```

## Rate Limiting Considerations

The Readwise API has strict rate limits:
- Default: 20 requests per minute
- Some endpoints allow up to 50 requests per minute

The code includes several strategies to handle these limitations:
1. Exponential backoff with the `backoff` library
2. Pre-fetching all existing documents once per sync run
3. Batch processing with conservative sleep periods between requests
4. Special handling for HTTP 429 (Too Many Requests) responses

## Implementation Details

The implementation is in `src/readwise.py` with these key components:

1. **URL Fetching**: `get_all_readwise_urls()` - Retrieves all document URLs from Readwise with pagination
2. **URL Checking**: `url_exists_in_readwise()` - Checks if a URL already exists to avoid duplicates  
3. **Adding Documents**: `add_to_readwise()` - Adds a single document to Readwise
4. **Batch Processing**: `batch_add_to_readwise()` - Processes multiple stories in batches

The main sync process is orchestrated from `src/main.py` in the `sync_with_readwise()` function.

## Error Handling

The code handles several error conditions:
- Network failures with retry logic
- Rate limiting with backoff and specific error messaging
- API errors with custom exceptions and fallbacks
- Missing data with graceful degradation

## Configuration

The integration requires a Readwise Reader API key set as an environment variable:
```bash
export READWISE_API_KEY=your_api_key_here
```

## Usage

From the command line:
```bash
# Basic usage with defaults
hn-poll sync

# Custom parameters
hn-poll sync --hours 48 --min-score 50 --min-relevance 80 --batch-size 5
```

## Future Maintenance Notes

When updating this code, pay attention to:

1. **API Changes**: Readwise may update their API endpoints or parameters
2. **Rate Limits**: Adjust batch sizes and sleep durations if rate limits change
3. **Retry Logic**: The backoff parameters might need tuning based on API behavior
4. **Error Handling**: Additional error conditions may need specific handling

The most likely point of failure is rate limiting, which is now handled with exponential backoff. However, if runs are consistently hitting limits, consider:

- Reducing batch sizes further
- Increasing delay between requests
- Implementing a more sophisticated queueing system
- Adding a resume-from-failure capability

For large-scale synchronization, the current pagination approach may need optimization as the number of documents in Readwise grows significantly.