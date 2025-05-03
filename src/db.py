import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any, Union, cast

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hn_stories.db')

def init_db() -> None:
    """Initialize the database with required tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
    table_exists = cursor.fetchone()
    
    # Create stories table if it doesn't exist
    if not table_exists:
        cursor.execute('''
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
        ''')
    else:
        # Check if columns exist and add them if not
        cursor.execute("PRAGMA table_info(stories)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'last_updated' not in columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN last_updated TEXT NOT NULL DEFAULT ''")
        if 'relevance_score' not in columns:
            cursor.execute("ALTER TABLE stories ADD COLUMN relevance_score INTEGER")
    
    # Create metadata table for tracking last poll time
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    # Insert initial metadata if they don't exist
    cursor.execute('''
    INSERT OR IGNORE INTO metadata (key, value)
    VALUES ('last_poll_time', ?)
    ''', (datetime.now().isoformat(),))
    
    cursor.execute('''
    INSERT OR IGNORE INTO metadata (key, value)
    VALUES ('last_oldest_id', '0')
    ''')
    
    conn.commit()
    conn.close()

def get_last_poll_time() -> Optional[str]:
    """Get the timestamp of the last successful poll.
    
    Returns:
        Optional[str]: ISO format timestamp string or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM metadata WHERE key = "last_poll_time"')
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return None

def update_last_poll_time() -> str:
    """Update the last poll time to current time.
    
    Returns:
        str: The new timestamp in ISO format
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = datetime.now().isoformat()
    cursor.execute('UPDATE metadata SET value = ? WHERE key = "last_poll_time"', (current_time,))
    
    conn.commit()
    conn.close()
    
    return current_time

def get_last_oldest_id() -> Optional[int]:
    """Get the ID of the oldest story from the last run.
    
    Returns:
        Optional[int]: The ID of the oldest story or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM metadata WHERE key = "last_oldest_id"')
    result = cursor.fetchone()
    
    conn.close()
    
    if result and result[0] != '0':
        return int(result[0])
    return None

def update_last_oldest_id(oldest_id: Optional[int]) -> None:
    """Update the ID of the oldest story from the current run.
    
    Args:
        oldest_id (Optional[int]): The ID of the oldest story processed
    """
    if not oldest_id:
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE metadata SET value = ? WHERE key = "last_oldest_id"', (str(oldest_id),))
    
    conn.commit()
    conn.close()

def save_stories(stories: List[Dict[str, Any]]) -> int:
    """Save new stories to the database.
    
    Args:
        stories (List[Dict[str, Any]]): List of story dictionaries to save
        
    Returns:
        int: Number of new stories saved
    """
    if not stories:
        return 0
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_count = 0
    
    for story in stories:
        # Check if story already exists
        cursor.execute('SELECT id FROM stories WHERE id = ?', (story['id'],))
        if cursor.fetchone() is None:
            # Add timestamp for new stories
            current_time = datetime.now().isoformat()
            
            cursor.execute('''
            INSERT INTO stories (
                id, title, url, score, by, time, timestamp, type, last_updated, relevance_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                story['id'],
                story.get('title', ''),
                story.get('url', ''),
                story.get('score', 0),
                story.get('by', ''),
                story.get('time', 0),
                current_time,
                story.get('type', 'story'),
                current_time,
                story.get('relevance_score', None)
            ))
            new_count += 1
    
    conn.commit()
    conn.close()
    
    return new_count

def update_story_scores(stories: List[Dict[str, Any]]) -> int:
    """Update scores for existing stories.
    
    Args:
        stories (List[Dict[str, Any]]): List of story dictionaries to update
        
    Returns:
        int: Number of stories updated
    """
    if not stories:
        return 0
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    update_count = 0
    current_time = datetime.now().isoformat()
    
    for story in stories:
        # Check if story exists
        cursor.execute('SELECT score, relevance_score FROM stories WHERE id = ?', (story['id'],))
        result = cursor.fetchone()
        
        if result is not None:
            # Unpack existing scores
            existing_score, existing_relevance = result
            
            # Determine what fields to update
            score_changed = existing_score != story.get('score', 0)
            relevance_provided = 'relevance_score' in story and story['relevance_score'] is not None
            relevance_changed = relevance_provided and existing_relevance != story['relevance_score']
            
            # Update only if something has changed
            if score_changed or relevance_changed:
                if relevance_provided:
                    cursor.execute('''
                    UPDATE stories
                    SET score = ?, last_updated = ?, relevance_score = ?
                    WHERE id = ?
                    ''', (
                        story.get('score', 0),
                        current_time,
                        story['relevance_score'],
                        story['id']
                    ))
                else:
                    cursor.execute('''
                    UPDATE stories
                    SET score = ?, last_updated = ?
                    WHERE id = ?
                    ''', (
                        story.get('score', 0),
                        current_time,
                        story['id']
                    ))
                update_count += 1
    
    conn.commit()
    conn.close()
    
    return update_count

def save_or_update_stories(stories: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Save new stories and update existing ones.
    
    Args:
        stories (List[Dict[str, Any]]): List of story dictionaries to save or update
        
    Returns:
        Tuple[int, int]: (new_count, update_count) - Number of new and updated stories
    """
    if not stories:
        return 0, 0
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_count = 0
    update_count = 0
    current_time = datetime.now().isoformat()
    
    for story in stories:
        # Check if story already exists
        cursor.execute('SELECT score, relevance_score FROM stories WHERE id = ?', (story['id'],))
        result = cursor.fetchone()
        
        if result is None:
            # New story - insert it
            cursor.execute('''
            INSERT INTO stories (
                id, title, url, score, by, time, timestamp, type, last_updated, relevance_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                story['id'],
                story.get('title', ''),
                story.get('url', ''),
                story.get('score', 0),
                story.get('by', ''),
                story.get('time', 0),
                current_time,
                story.get('type', 'story'),
                current_time,
                story.get('relevance_score', None)
            ))
            new_count += 1
        else:
            # Unpack existing scores
            existing_score, existing_relevance = result
            
            # Determine what fields to update
            score_changed = existing_score != story.get('score', 0)
            relevance_provided = 'relevance_score' in story and story['relevance_score'] is not None
            relevance_changed = relevance_provided and existing_relevance != story['relevance_score']
            
            # Update only if something has changed
            if score_changed or relevance_changed:
                if relevance_provided:
                    cursor.execute('''
                    UPDATE stories
                    SET score = ?, last_updated = ?, relevance_score = ?
                    WHERE id = ?
                    ''', (
                        story.get('score', 0),
                        current_time,
                        story['relevance_score'],
                        story['id']
                    ))
                else:
                    cursor.execute('''
                    UPDATE stories
                    SET score = ?, last_updated = ?
                    WHERE id = ?
                    ''', (
                        story.get('score', 0),
                        current_time,
                        story['id']
                    ))
                update_count += 1
    
    conn.commit()
    conn.close()
    
    return new_count, update_count

def get_stories_within_timeframe(hours: int = 24, min_score: int = 0, min_relevance: Optional[int] = None, only_unscored: bool = False) -> List[Dict[str, Any]]:
    """Get all stories within the specified timeframe with filtering options.
    
    Args:
        hours (int): Number of hours to look back
        min_score (int): Minimum HN score threshold
        min_relevance (Optional[int]): Minimum relevance score threshold
        only_unscored (bool): If True, only return stories without a relevance score
        
    Returns:
        List[Dict[str, Any]]: List of story dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Calculate cutoff time in UTC for consistent timezone handling
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    cutoff_timestamp = int(cutoff_time.timestamp())
    
    # Base query for the time period and HN score
    query = 'SELECT * FROM stories WHERE time >= ? AND score >= ?'
    params = [cutoff_timestamp, min_score]
    
    # Add relevance score filters if needed
    if only_unscored:
        # Only unscored stories
        query += ' AND relevance_score IS NULL'
    elif min_relevance is not None:
        # Only stories with relevance >= threshold
        query += ' AND relevance_score >= ?'
        params.append(min_relevance)
    
    # Add ordering - sort by either relevance score or HN score
    if min_relevance is not None:
        # Primary sort by relevance, secondary by HN score
        query += ' ORDER BY relevance_score DESC, score DESC'
    else:
        # Sort by HN score only
        query += ' ORDER BY score DESC'
    
    # Execute query
    cursor.execute(query, tuple(params))
    
    rows = cursor.fetchall()
    stories = [dict(row) for row in rows]
    
    conn.close()
    
    return stories

def get_high_quality_stories(hours: int = 24, min_hn_score: int = 30, min_relevance: int = 75) -> List[Dict[str, Any]]:
    """Get high-quality stories meeting both HN score and relevance thresholds.
    
    Args:
        hours (int): Number of hours to look back
        min_hn_score (int): Minimum HN score threshold
        min_relevance (int): Minimum relevance score threshold
        
    Returns:
        List[Dict[str, Any]]: List of story dictionaries meeting the criteria
    """
    # Simply use our optimized get_stories_within_timeframe function
    return get_stories_within_timeframe(
        hours=hours,
        min_score=min_hn_score,
        min_relevance=min_relevance
    )

def get_unscored_stories(hours: Optional[int] = None, min_score: int = 0) -> List[Dict[str, Any]]:
    """Get stories without relevance scores.
    
    Args:
        hours (Optional[int]): Number of hours to look back. If None, gets all unscored stories.
        min_score (int): Minimum HN score threshold
        
    Returns:
        List[Dict[str, Any]]: List of story dictionaries without relevance scores
    """
    if hours is not None:
        # Get stories from the specified time period
        return get_stories_within_timeframe(
            hours=hours,
            min_score=min_score,
            only_unscored=True
        )
    else:
        # Get all unscored stories without time constraint
        return get_all_unscored_stories(min_score=min_score)

def get_unscored_stories_in_batches(hours: Optional[int] = None, min_score: int = 0, batch_size: int = 10) -> List[List[Dict[str, Any]]]:
    """Get unscored stories in batches for efficient processing.
    
    Args:
        hours (Optional[int]): Number of hours to look back. If None, gets all unscored stories.
        min_score (int): Minimum score threshold
        batch_size (int): Number of stories to retrieve in each batch
        
    Returns:
        List[List[Dict[str, Any]]]: List of batches of story dictionaries
    """
    # Get all unscored stories
    all_stories = get_unscored_stories(hours=hours, min_score=min_score)
    
    # Split into batches
    batches: List[List[Dict[str, Any]]] = []
    for i in range(0, len(all_stories), batch_size):
        batch = all_stories[i:i + batch_size]
        if batch:  # Only add non-empty batches
            batches.append(batch)
    
    return batches

def get_all_unscored_stories(min_score: int = 0) -> List[Dict[str, Any]]:
    """Get all unscored stories regardless of age.
    
    Args:
        min_score (int): Minimum score threshold
        
    Returns:
        List[Dict[str, Any]]: List of story dictionaries
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # First check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        return []
    
    # Query for all stories without a relevance score
    query = 'SELECT * FROM stories WHERE relevance_score IS NULL AND score >= ?'
    params = [min_score]
    
    # Add ordering
    query += ' ORDER BY score DESC'
    
    # Execute query
    cursor.execute(query, tuple(params))
    
    rows = cursor.fetchall()
    stories = [dict(row) for row in rows]
    
    conn.close()
    
    return stories

def get_story_ids_since(timestamp_str: Optional[str] = None) -> List[int]:
    """Get IDs of stories added since the specified timestamp.
    
    Args:
        timestamp_str (Optional[str]): ISO format timestamp string
        
    Returns:
        List[int]: List of story IDs
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if timestamp_str:
        cursor.execute('SELECT id FROM stories WHERE timestamp > ?', (timestamp_str,))
    else:
        cursor.execute('SELECT id FROM stories')
        
    story_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return story_ids

def get_story_with_content(story_id: int) -> Optional[Dict[str, Any]]:
    """Get full story details.
    
    Args:
        story_id (int): The ID of the story to retrieve
        
    Returns:
        Optional[Dict[str, Any]]: Story details or None if not found
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM stories WHERE id = ?
    ''', (story_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    story = dict(row)
    
    return story

def get_relevance_score_stats() -> Dict[str, Union[int, float]]:
    """Get statistics about relevance scores in the database.
    
    Returns:
        Dict[str, Union[int, float]]: Statistics about relevance scores
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        return {
            'total_stories': 0,
            'scored_stories': 0,
            'unscored_stories': 0,
            'avg_score': 0,
            'min_score': 0,
            'max_score': 0
        }
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM stories')
    total_stories = cursor.fetchone()[0]
    
    # Get scored count
    cursor.execute('SELECT COUNT(*) FROM stories WHERE relevance_score IS NOT NULL')
    scored_stories = cursor.fetchone()[0]
    
    # Calculate unscored
    unscored_stories = total_stories - scored_stories
    
    # Get stats for scores
    if scored_stories > 0:
        cursor.execute('SELECT AVG(relevance_score), MIN(relevance_score), MAX(relevance_score) FROM stories WHERE relevance_score IS NOT NULL')
        avg_score, min_score, max_score = cursor.fetchone()
    else:
        avg_score, min_score, max_score = 0, 0, 0
    
    conn.close()
    
    return {
        'total_stories': total_stories,
        'scored_stories': scored_stories,
        'unscored_stories': unscored_stories,
        'avg_score': round(avg_score, 1) if avg_score else 0,
        'min_score': min_score or 0,
        'max_score': max_score or 0
    }