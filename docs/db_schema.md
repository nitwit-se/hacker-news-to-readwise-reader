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
    type TEXT NOT NULL
)
```

The `stories` table stores all Hacker News stories with their associated metadata.

#### Field Descriptions:

- `id`: The unique identifier for the story (from Hacker News API)
- `title`: The title of the story
- `url`: The URL of the story (may be null for "Ask HN" posts)
- `score`: The current score/points of the story
- `by`: The username of the story submitter
- `time`: The Unix timestamp of the story submission
- `timestamp`: The formatted timestamp of when the story was added to our database
- `type`: The type of the story (e.g., "story", "job", "poll")

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

### Get All Stories

```sql
SELECT id, title, url, score 
FROM stories 
ORDER BY timestamp DESC
```