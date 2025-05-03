"""
Database fixtures for testing.
"""

import sqlite3
from typing import List, Dict, Any
from datetime import datetime, timedelta
import time


def create_test_story(
    id: int = 39428394,
    title: str = "Test Story",
    url: str = "https://example.com/test",
    score: int = 42,
    by: str = "test_user",
    timestamp: int = None,
    hours_ago: int = 12,
    relevance_score: int = None,
) -> Dict[str, Any]:
    """
    Create a test story with specified parameters.
    
    Args:
        id: Story ID
        title: Story title
        url: Story URL
        score: HN score
        by: Submitter username
        timestamp: Unix timestamp (if None, calculated from hours_ago)
        hours_ago: Hours ago from now (only used if timestamp is None)
        relevance_score: Optional relevance score
        
    Returns:
        Dict[str, Any]: Story dictionary
    """
    # Calculate timestamp if not provided
    if timestamp is None:
        dt = datetime.now() - timedelta(hours=hours_ago)
        timestamp = int(dt.timestamp())
    
    # Create base story
    story = {
        "id": id,
        "title": title,
        "url": url,
        "score": score,
        "by": by,
        "time": timestamp,
        "type": "story",
        "timestamp": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat(),
    }
    
    # Add relevance score if provided
    if relevance_score is not None:
        story["relevance_score"] = relevance_score
        
    return story


def create_test_stories(count: int = 5, base_id: int = 39428394, hours_range: int = 48) -> List[Dict[str, Any]]:
    """
    Create a list of test stories with different ages and scores.
    
    Args:
        count: Number of stories to create
        base_id: Starting ID for stories
        hours_range: Maximum hours ago for oldest story
        
    Returns:
        List[Dict[str, Any]]: List of story dictionaries
    """
    stories = []
    
    for i in range(count):
        id = base_id + i
        # Vary the scores (10-200)
        score = 10 + (i * 40) % 190
        # Vary the age (0 to hours_range hours ago)
        hours_ago = (i * hours_range // count)
        # Vary the relevance (None, or 0-100)
        relevance_score = None if i % 3 == 0 else (i * 20) % 100
        
        story = create_test_story(
            id=id,
            title=f"Test Story {i+1}",
            url=f"https://example.com/test-{i+1}",
            score=score,
            by=f"user_{i+1}",
            hours_ago=hours_ago,
            relevance_score=relevance_score
        )
        
        stories.append(story)
    
    return stories


def populate_test_db(db_connection, stories: List[Dict[str, Any]]) -> None:
    """
    Populate a test database with the provided stories.
    
    Args:
        db_connection: SQLite database connection
        stories: List of story dictionaries to insert
    """
    cursor = db_connection.cursor()
    
    # Insert stories
    for story in stories:
        cursor.execute('''
        INSERT INTO stories (
            id, title, url, score, by, time, timestamp, type, last_updated, relevance_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            story['id'],
            story['title'],
            story['url'],
            story['score'],
            story['by'],
            story['time'],
            story['timestamp'],
            story['type'],
            story['last_updated'],
            story.get('relevance_score')
        ))
    
    # Set up metadata
    current_time = datetime.now().isoformat()
    cursor.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)', 
                   ('last_poll_time', current_time))
    
    if stories:
        oldest_id = min(story['id'] for story in stories)
        cursor.execute('INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)', 
                       ('last_oldest_id', str(oldest_id)))
    
    db_connection.commit()


def get_test_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a connection to the test database.
    
    Args:
        db_path: Path to the test database file
        
    Returns:
        sqlite3.Connection: Database connection
    """
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection