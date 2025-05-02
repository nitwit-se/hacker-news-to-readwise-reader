# Database Schema

This document outlines the database schema used in the Hacker News Poller project.

## Tables

### Stories Table

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
```

The `stories` table stores all Hacker News stories with their associated metadata and content.

#### Field Descriptions:

- `id`: The unique identifier for the story (from Hacker News API)
- `title`: The title of the story
- `url`: The URL of the story (may be null for "Ask HN" posts)
- `score`: The current score/points of the story
- `by`: The username of the story submitter
- `time`: The Unix timestamp of the story submission
- `timestamp`: The formatted timestamp of when the story was added to our database
- `type`: The type of the story (e.g., "story", "job", "poll")
- `content`: The extracted content from the story URL
- `content_fetched`: Status of content fetching (see status codes below)
- `error_type`: Type of error encountered during content fetching (if any)
- `error_message`: Detailed error message (if any)
- `error_status`: HTTP status code from fetching (if applicable)
- `last_fetch_attempt`: Timestamp of the last attempt to fetch content

#### Content Fetched Status Codes:

- `0`: Content has not been fetched yet
- `1`: Content was successfully fetched
- `2`: Content fetch was attempted but failed with an error
- `3`: Content is known to be unavailable (e.g., Twitter URLs)

### Metadata Table

```sql
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
```

The `metadata` table stores application-level metadata, such as the last time stories were fetched.

#### Field Descriptions:

- `key`: The name of the metadata field
- `value`: The value of the metadata field

## Common Queries

### Get New Stories

```sql
SELECT * FROM stories 
WHERE timestamp > (SELECT value FROM metadata WHERE key = 'last_run')
ORDER BY score DESC
```

### Get Stories with Successful Content

```sql
SELECT id, title, url, score, content 
FROM stories 
WHERE content_fetched = 1
ORDER BY timestamp DESC
```

### Get Failed Content Fetches

```sql
SELECT id, title, url, error_type, error_message, error_status 
FROM stories 
WHERE content_fetched = 2
```