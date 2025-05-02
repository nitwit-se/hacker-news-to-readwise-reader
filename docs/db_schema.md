# Database Schema

This document outlines the database schema used in the Hacker News Poller project.

## Overview

The Hacker News Poller uses a SQLite database to store story data and application metadata. The database helps track stories over time, update their scores, and optimize performance for future runs.

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
    last_updated TEXT NOT NULL,
    relevance_score INTEGER
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
- `relevance_score`: A score from 0 to 100 indicating the story's relevance to user interests (higher is more relevant)

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
AND score >= 30
ORDER BY score DESC
```

### Get Stories with High Relevance Scores

```sql
SELECT * FROM stories 
WHERE time >= (strftime('%s', 'now') - 24*60*60)
AND score >= 30
AND relevance_score >= 75
ORDER BY relevance_score DESC, score DESC
```

### Get Unscored Stories for Processing

```sql
SELECT * FROM stories 
WHERE relevance_score IS NULL
AND score >= 30
ORDER BY score DESC
```

### Update Story Score

```sql
UPDATE stories
SET score = ?, last_updated = ?
WHERE id = ?
```

### Update Story with Relevance Score

```sql
UPDATE stories
SET score = ?, last_updated = ?, relevance_score = ?
WHERE id = ?
```

### Get Relevance Statistics

```sql
SELECT 
  COUNT(*) as total_stories,
  SUM(CASE WHEN relevance_score IS NOT NULL THEN 1 ELSE 0 END) as scored_stories,
  AVG(relevance_score) as avg_score,
  MIN(relevance_score) as min_score,
  MAX(relevance_score) as max_score
FROM stories
```

## Application Workflow

The database is used in three distinct operational modes:

1. **Fetch Mode** - Retrieving and storing stories:
   - Get the last poll time and oldest ID
   - Save new stories and update existing ones
   - Update metadata for the next run

2. **Score Mode** - Calculating relevance scores:
   - Retrieve unscored stories
   - Update stories with new relevance scores

3. **Show Mode** - Displaying filtered stories:
   - Filter stories by time period and HN score
   - Filter stories by relevance score
   - Sort and display results