import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hn_stories.db')

def init_db():
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
            type TEXT NOT NULL
        )
        ''')
    
    # Create metadata table for tracking last poll time
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    # Insert initial last_poll_time if it doesn't exist
    cursor.execute('''
    INSERT OR IGNORE INTO metadata (key, value)
    VALUES ('last_poll_time', ?)
    ''', (datetime.now().isoformat(),))
    
    conn.commit()
    conn.close()

def get_last_poll_time():
    """Get the timestamp of the last successful poll."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM metadata WHERE key = "last_poll_time"')
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    return None

def update_last_poll_time():
    """Update the last poll time to current time."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = datetime.now().isoformat()
    cursor.execute('UPDATE metadata SET value = ? WHERE key = "last_poll_time"', (current_time,))
    
    conn.commit()
    conn.close()
    
    return current_time

def save_stories(stories):
    """Save new stories to the database.
    
    Args:
        stories (list): List of story dictionaries to save
        
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
                id, title, url, score, by, time, timestamp, type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                story['id'],
                story.get('title', ''),
                story.get('url', ''),
                story.get('score', 0),
                story.get('by', ''),
                story.get('time', 0),
                current_time,
                story.get('type', 'story')
            ))
            new_count += 1
    
    conn.commit()
    conn.close()
    
    return new_count

def get_story_ids_since(timestamp_str=None):
    """Get IDs of stories added since the specified timestamp.
    
    Args:
        timestamp_str (str): ISO format timestamp string
        
    Returns:
        list: List of story IDs
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

def get_story_with_content(story_id):
    """Get full story details.
    
    Args:
        story_id (int): The ID of the story to retrieve
        
    Returns:
        dict: Story details or None if not found
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