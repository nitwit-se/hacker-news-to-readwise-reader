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
    last_updated TEXT NOT NULL
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
- `last_updated`: The formatted timestamp of when the story was last updated in our database

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

#### Common Metadata Keys:

- `last_poll_time`: The ISO-formatted timestamp of the last successful poll
- `last_oldest_id`: The ID of the oldest story processed in the previous run, used to optimize future fetches

## Common Queries

### Get High-Scoring Stories from Past 24 Hours

```sql
SELECT * FROM stories 
WHERE time >= (strftime('%s', 'now') - 24*60*60)
AND score >= 10
ORDER BY score DESC
```

### Update Story Score

```sql
UPDATE stories
SET score = ?, last_updated = ?
WHERE id = ?
```

### Check for Stories Within Timeframe

```sql
SELECT * FROM stories 
WHERE time >= ?
AND score >= ?
ORDER BY score DESC
```