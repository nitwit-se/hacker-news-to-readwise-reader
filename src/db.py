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
            type TEXT NOT NULL,
            content TEXT,
            content_fetched INTEGER DEFAULT 0,
            error_type TEXT,
            error_message TEXT,
            error_status INTEGER,
            last_fetch_attempt TEXT
        )
        ''')
    else:
        # Ensure the content columns exist
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(stories)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add content column if it doesn't exist
        if 'content' not in columns:
            cursor.execute('ALTER TABLE stories ADD COLUMN content TEXT')
        
        # Add content_fetched column if it doesn't exist
        if 'content_fetched' not in columns:
            cursor.execute('ALTER TABLE stories ADD COLUMN content_fetched INTEGER DEFAULT 0')
            
        # Add error columns if they don't exist
        if 'error_type' not in columns:
            cursor.execute('ALTER TABLE stories ADD COLUMN error_type TEXT')
            
        if 'error_message' not in columns:
            cursor.execute('ALTER TABLE stories ADD COLUMN error_message TEXT')
            
        if 'error_status' not in columns:
            cursor.execute('ALTER TABLE stories ADD COLUMN error_status INTEGER')
            
        if 'last_fetch_attempt' not in columns:
            cursor.execute('ALTER TABLE stories ADD COLUMN last_fetch_attempt TEXT')
    
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
    
    # List of domains to automatically mark as unavailable
    unavailable_domains = [
        'twitter.com',
        'x.com',
        't.co'
    ]
    
    for story in stories:
        # Check if story already exists
        cursor.execute('SELECT id FROM stories WHERE id = ?', (story['id'],))
        if cursor.fetchone() is None:
            # Add timestamp for new stories
            current_time = datetime.now().isoformat()
            
            # Check if URL is from a site that blocks content fetching
            url = story.get('url', '')
            content_fetched = 0
            error_type = None
            error_message = None
            
            if url:
                from urllib.parse import urlparse
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.lower()
                if domain.startswith('www.'):
                    domain = domain[4:]
                
                # Automatically mark Twitter/X URLs as unavailable
                if domain in unavailable_domains:
                    content_fetched = 3  # Special status for known unavailable content
                    error_type = 'UnavailableContent'
                    error_message = f'Content from {domain} is not available'
            
            cursor.execute('''
            INSERT INTO stories (
                id, title, url, score, by, time, timestamp, type, 
                content, content_fetched, error_type, error_message, 
                error_status, last_fetch_attempt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                story['id'],
                story.get('title', ''),
                url,
                story.get('score', 0),
                story.get('by', ''),
                story.get('time', 0),
                current_time,
                story.get('type', 'story'),
                story.get('content', None),
                content_fetched,
                error_type,
                error_message,
                story.get('error_status', None),
                current_time if content_fetched == 3 else None
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
    """Get full story details including content if available.
    
    Args:
        story_id (int): The ID of the story to retrieve
        
    Returns:
        dict: Story details including content or None if not found
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
    
    # Add content_summary if content is available
    if story.get('content') and story.get('content_fetched') == 1:
        # Get first 200 characters of content as summary
        content = story['content'].replace('\n', ' ').strip()
        if len(content) > 200:
            story['content_summary'] = content[:200] + '...'
        else:
            story['content_summary'] = content
    elif story.get('error_type'):
        # Add error message as content summary if fetch failed
        error_type = story.get('error_type')
        error_msg = story.get('error_message', '')
        story['content_summary'] = f"[Error: {error_type}] {error_msg}"
    elif story.get('content_fetched') == 3:
        # Special status for known unavailable content (e.g., Twitter)
        domain = "Twitter/X"
        if story.get('url'):
            from urllib.parse import urlparse
            parsed_url = urlparse(story.get('url'))
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
        story['content_summary'] = f"[{domain} content not available - view directly on the website]"
            
    return story

def update_story_content(story_id, content=None, error_info=None):
    """Update a story with fetched content or error information.
    
    Args:
        story_id (int): The ID of the story to update
        content (str, optional): The markdown content to save
        error_info (dict, optional): Error information if content fetch failed
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    current_time = datetime.now().isoformat()
    
    if content:
        # Successful content fetch
        cursor.execute('''
        UPDATE stories 
        SET content = ?, content_fetched = 1, 
            error_type = NULL, error_message = NULL, error_status = NULL,
            last_fetch_attempt = ?
        WHERE id = ?
        ''', (content, current_time, story_id))
    elif error_info:
        # Failed content fetch with error information
        cursor.execute('''
        UPDATE stories 
        SET content_fetched = 2,
            error_type = ?, error_message = ?, error_status = ?,
            last_fetch_attempt = ?
        WHERE id = ?
        ''', (
            error_info.get('error_type'),
            error_info.get('error_message'),
            error_info.get('error_status'),
            current_time,
            story_id
        ))
    else:
        # No content and no error info, just mark as attempted
        cursor.execute('''
        UPDATE stories 
        SET content_fetched = 2,
            error_type = 'Unknown', error_message = 'No content or error info provided',
            last_fetch_attempt = ?
        WHERE id = ?
        ''', (current_time, story_id))
    
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    
    return affected > 0

def get_stories_needing_content(limit=10, retry_failed=False, retry_after_hours=24):
    """Get stories that have URLs but haven't had content fetched yet.
    
    Args:
        limit (int): Maximum number of stories to retrieve
        retry_failed (bool): Whether to retry stories that previously failed
        retry_after_hours (int): Only retry stories that failed more than this many hours ago
        
    Returns:
        list: List of story dictionaries with id and url
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # By default, only get stories that have never been attempted
    if not retry_failed:
        cursor.execute('''
        SELECT id, url FROM stories 
        WHERE url IS NOT NULL 
        AND url != '' 
        AND content_fetched = 0
        AND (
            -- Skip stories marked with unavailable content (e.g., Twitter)
            NOT (
                -- Match twitter.com domains more precisely
                url LIKE 'https://twitter.com/%' OR
                url LIKE 'http://twitter.com/%' OR
                url LIKE 'https://www.twitter.com/%' OR
                url LIKE 'http://www.twitter.com/%' OR
                -- Match x.com domains precisely
                url LIKE 'https://x.com/%' OR
                url LIKE 'http://x.com/%' OR
                url LIKE 'https://www.x.com/%' OR
                url LIKE 'http://www.x.com/%' OR
                -- Match t.co shortened links
                url LIKE 'https://t.co/%' OR
                url LIKE 'http://t.co/%'
            )
        )
        LIMIT ?
        ''', (limit,))
    else:
        # For retries, get stories that failed but exclude ones that failed recently
        # and exclude specific error types that we know won't succeed
        cursor.execute('''
        SELECT id, url, error_type FROM stories 
        WHERE url IS NOT NULL 
        AND url != '' 
        AND (
            content_fetched = 0
            OR (
                content_fetched = 2 
                AND last_fetch_attempt < datetime('now', ?) 
                AND error_type NOT IN ('ProblematicDomain', 'Forbidden', 'NotFound', 'UnavailableContent')
            )
        )
        AND content_fetched != 3  -- Skip stories marked with unavailable content
        AND NOT (
            -- Match twitter.com domains more precisely
            url LIKE 'https://twitter.com/%' OR
            url LIKE 'http://twitter.com/%' OR
            url LIKE 'https://www.twitter.com/%' OR
            url LIKE 'http://www.twitter.com/%' OR
            -- Match x.com domains precisely
            url LIKE 'https://x.com/%' OR
            url LIKE 'http://x.com/%' OR
            url LIKE 'https://www.x.com/%' OR
            url LIKE 'http://www.x.com/%' OR
            -- Match t.co shortened links
            url LIKE 'https://t.co/%' OR
            url LIKE 'http://t.co/%'
        )
        LIMIT ?
        ''', (f'-{retry_after_hours} hours', limit))
    
    stories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return stories