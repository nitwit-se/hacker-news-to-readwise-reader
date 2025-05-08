"""
Unit tests for the Readwise sync functionality in src.main module.
"""

import pytest
import responses
import sqlite3
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.main import (
    sync_with_readwise, cmd_sync
)
from src.readwise import get_all_readwise_urls, batch_add_to_readwise
from tests.fixtures.db_fixtures import ensure_readwise_columns


@pytest.mark.unit
def test_sync_with_readwise_max_stories(mock_db_path, monkeypatch):
    """Test that max_stories limits the number of stories synced."""
    # Create test stories
    import sqlite3
    
    # Create a connection to the test database
    conn = sqlite3.connect(mock_db_path)
    
    # Initialize tables
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stories (
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
    
    # Ensure Readwise columns exist
    ensure_readwise_columns(conn)
    
    # Create metadata table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    # Insert initial metadata
    cursor.execute('''
    INSERT OR IGNORE INTO metadata (key, value)
    VALUES ('last_readwise_sync_time', ?)
    ''', (datetime.now().isoformat(),))
    
    # Create multiple unsynced stories
    current_time = int(datetime.now().timestamp())
    for i in range(10):
        cursor.execute('''
        INSERT INTO stories (
            id, title, url, score, by, time, timestamp, type, last_updated, relevance_score, readwise_synced
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            1000 + i,
            f"Test Story {i}",
            f"https://example.com/test-{i}",
            50 + i,
            "test_user",
            current_time - 3600,
            datetime.now().isoformat(),
            "story",
            datetime.now().isoformat(),
            80 + i,
            0
        ))
    
    conn.commit()
    conn.close()
    
    # Mock the get_unsynced_stories function to return filtered stories
    mock_unsynced = MagicMock(return_value=[
        {"id": 1000, "title": "Test Story 1", "url": "https://example.com/1", "score": 50, "relevance_score": 80},
        {"id": 1001, "title": "Test Story 2", "url": "https://example.com/2", "score": 51, "relevance_score": 81},
        {"id": 1002, "title": "Test Story 3", "url": "https://example.com/3", "score": 52, "relevance_score": 82}
    ])
    monkeypatch.setattr('src.main.get_unsynced_stories', mock_unsynced)
    
    # Mock the batch_add_to_readwise function
    mock_batch_add = MagicMock(return_value=([1000, 1001, 1002], []))
    monkeypatch.setattr('src.main.batch_add_to_readwise', mock_batch_add)
    
    # Mock the mark_stories_as_synced function
    mock_mark_synced = MagicMock(return_value=3)
    monkeypatch.setattr('src.main.mark_stories_as_synced', mock_mark_synced)
    
    # Mock environment variable for Readwise API key
    monkeypatch.setenv("READWISE_API_KEY", "test_key")
    
    # Mock the get_all_readwise_urls function
    mock_get_urls = MagicMock(return_value=set())
    monkeypatch.setattr('src.readwise.get_all_readwise_urls', mock_get_urls)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        # Test with max_stories=3
        result = sync_with_readwise(
            hours=24,
            min_hn_score=30,
            min_relevance=75,
            batch_size=10,
            max_stories=3,
            min_comments=30  # Add min_comments parameter
        )
    
    # Check that the result is correct
    assert result == 3
    
    # Check that batch_add_to_readwise was called with the right number of stories
    args, _ = mock_batch_add.call_args
    stories_arg = args[0]
    assert len(stories_arg) == 3


@pytest.mark.unit
def test_sync_with_readwise_without_max_stories(mock_db_path, monkeypatch):
    """Test that without max_stories, all stories are synced."""
    # Create test stories
    import sqlite3
    
    # Create a connection to the test database
    conn = sqlite3.connect(mock_db_path)
    
    # Initialize tables
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stories (
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
    
    # Ensure Readwise columns exist
    ensure_readwise_columns(conn)
    
    # Create metadata table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    # Insert initial metadata
    cursor.execute('''
    INSERT OR IGNORE INTO metadata (key, value)
    VALUES ('last_readwise_sync_time', ?)
    ''', (datetime.now().isoformat(),))
    
    # Create multiple unsynced stories
    current_time = int(datetime.now().timestamp())
    for i in range(10):
        cursor.execute('''
        INSERT INTO stories (
            id, title, url, score, by, time, timestamp, type, last_updated, relevance_score, readwise_synced
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            2000 + i,
            f"Test Story {i}",
            f"https://example.com/test-{i}",
            50 + i,
            "test_user",
            current_time - 3600,
            datetime.now().isoformat(),
            "story",
            datetime.now().isoformat(),
            80 + i,
            0
        ))
    
    conn.commit()
    conn.close()
    
    # Mock the get_unsynced_stories function to return filtered stories
    stories = []
    for i in range(10):
        stories.append({
            "id": 2000 + i, 
            "title": f"Test Story {i}", 
            "url": f"https://example.com/test-{i}", 
            "score": 50 + i, 
            "relevance_score": 80 + i
        })
    
    mock_unsynced = MagicMock(return_value=stories)
    monkeypatch.setattr('src.main.get_unsynced_stories', mock_unsynced)
    
    # Mock the batch_add_to_readwise function
    mock_batch_add = MagicMock(return_value=([2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009], []))
    monkeypatch.setattr('src.main.batch_add_to_readwise', mock_batch_add)
    
    # Mock the mark_stories_as_synced function
    mock_mark_synced = MagicMock(return_value=10)
    monkeypatch.setattr('src.main.mark_stories_as_synced', mock_mark_synced)
    
    # Mock environment variable for Readwise API key
    monkeypatch.setenv("READWISE_API_KEY", "test_key")
    
    # Mock the get_all_readwise_urls function
    mock_get_urls = MagicMock(return_value=set())
    monkeypatch.setattr('src.readwise.get_all_readwise_urls', mock_get_urls)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        # Test without max_stories
        result = sync_with_readwise(
            hours=24,
            min_hn_score=30,
            min_relevance=75,
            batch_size=10,
            min_comments=30  # Add min_comments parameter
        )
    
    # Check that the result is correct
    assert result == 10
    
    # Check that batch_add_to_readwise was called with all stories
    args, _ = mock_batch_add.call_args
    stories_arg = args[0]
    assert len(stories_arg) == 10


@pytest.mark.unit
def test_cmd_sync(monkeypatch):
    """Test the sync command handler."""
    # Create mock args
    class MockArgs:
        hours = 24
        min_score = 30
        min_relevance = 75
        batch_size = 10
        max_stories = 5
        no_relevance_filter = False
        min_comments = 30  # Add min_comments
    
    # Mock sync_with_readwise to avoid actual syncing
    mock_sync = MagicMock(return_value=5)
    monkeypatch.setattr('src.main.sync_with_readwise', mock_sync)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        result = cmd_sync(MockArgs())
    
    assert result == 0  # Should return success
    
    # Verify mock was called with correct args
    mock_sync.assert_called_with(
        hours=24,
        min_hn_score=30,
        min_relevance=75,
        batch_size=5,  # Note: should be min(args.batch_size, 5)
        max_stories=5,
        min_comments=30  # Add min_comments
    )


@pytest.mark.unit
def test_cmd_sync_no_relevance_filter(monkeypatch):
    """Test the sync command handler with relevance filtering disabled."""
    # Create mock args
    class MockArgs:
        hours = 24
        min_score = 30
        min_relevance = 75
        batch_size = 10
        max_stories = 5
        no_relevance_filter = True
        min_comments = 30  # Add min_comments
    
    # Mock sync_with_readwise to avoid actual syncing
    mock_sync = MagicMock(return_value=8)
    monkeypatch.setattr('src.main.sync_with_readwise', mock_sync)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        result = cmd_sync(MockArgs())
    
    assert result == 0  # Should return success
    
    # Verify mock was called with correct args
    mock_sync.assert_called_with(
        hours=24,
        min_hn_score=30,
        min_relevance=75,  # Now it should use the min_relevance value even with no_relevance_filter=True
        batch_size=5,  # Note: should be min(args.batch_size, 5)
        max_stories=5,
        min_comments=30  # Add min_comments
    )