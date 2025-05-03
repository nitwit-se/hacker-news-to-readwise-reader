"""
Unit tests for src.main module.
"""

import pytest
import responses
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.main import (
    calculate_combined_score, format_story, 
    fetch_stories_async, score_stories_async, show_stories,
    cmd_fetch, cmd_score, cmd_show, main
)
from tests.fixtures.mock_api import mock_hn_api, mock_hn_api_async
from tests.fixtures.mock_anthropic import mock_anthropic, mock_async_anthropic


@pytest.mark.unit
def test_calculate_combined_score():
    """Test calculating a combined score from HN and relevance scores."""
    # Test with both scores
    story = {
        "id": 1,
        "score": 100,
        "relevance_score": 80
    }
    
    # Default weights
    score = calculate_combined_score(story)
    assert 0 <= score <= 100
    
    # Higher HN weight
    score_hn_heavy = calculate_combined_score(story, hn_weight=0.9)
    
    # Higher relevance weight
    score_relevance_heavy = calculate_combined_score(story, hn_weight=0.1)
    
    # HN-heavy score should be different than relevance-heavy
    assert score_hn_heavy != score_relevance_heavy
    
    # Test with very high HN score
    story = {
        "id": 2,
        "score": 1000,
        "relevance_score": 50
    }
    
    score = calculate_combined_score(story)
    assert 0 <= score <= 100
    
    # Test with missing relevance score
    story = {
        "id": 3,
        "score": 100,
        "relevance_score": None
    }
    
    score = calculate_combined_score(story)
    assert 0 <= score <= 100
    
    # Test with no relevance score key
    story = {
        "id": 4,
        "score": 100
    }
    
    score = calculate_combined_score(story)
    assert 0 <= score <= 100


@pytest.mark.unit
def test_format_story():
    """Test formatting a story for console output."""
    # Basic story with all fields
    story = {
        "id": 12345,
        "title": "Test Story Title",
        "url": "https://example.com/test",
        "score": 100,
        "by": "test_user",
        "time": int(datetime.now().timestamp()) - 3600,  # 1 hour ago
        "type": "story"
    }
    
    # Format with basic fields
    output = format_story(story)
    assert story["title"] in output
    assert story["url"] in output
    assert str(story["score"]) in output
    assert story["by"] in output
    assert str(story["id"]) in output
    
    # Add relevance score
    story["relevance_score"] = 85
    output = format_story(story)
    assert "Relevance: 85" in output
    
    # Add combined score
    story["combined_score"] = 92.5
    output = format_story(story)
    assert "Combined: 92.5" in output
    
    # Test without URL (Ask HN type)
    story_no_url = {
        "id": 12346,
        "title": "Ask HN: Test Question",
        "score": 50,
        "by": "test_user",
        "time": int(datetime.now().timestamp()) - 7200,  # 2 hours ago
        "type": "story"
    }
    
    output = format_story(story_no_url)
    assert f"URL: https://news.ycombinator.com/item?id={story_no_url['id']}" in output


@pytest.mark.unit
@pytest.mark.asyncio
@responses.activate
async def test_fetch_stories_async(mock_db_path, monkeypatch):
    """Test fetching stories asynchronously."""
    # Instead of actually trying to hit the API, we'll mock the filtered_stories function
    # which is the core of what fetch_stories_async calls
    
    # Mock get_filtered_stories_async to return fake results
    async def mock_get_filtered_stories(*args, **kwargs):
        # Return some fake stories and an ID
        return [
            {
                "id": 12345,
                "title": "Test Story",
                "url": "https://example.com",
                "score": 100,
                "by": "test_user",
                "time": int(datetime.now().timestamp()) - 3600  # 1 hour ago
            }
        ], 12345
    
    # Apply the mock
    monkeypatch.setattr("src.main.get_filtered_stories_async", mock_get_filtered_stories)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        # Call the function
        new_count, update_count = await fetch_stories_async(
            hours=24,
            min_score=10,
            source='top',
            limit=5
        )
    
    # Should have added some stories
    assert isinstance(new_count, int)
    assert isinstance(update_count, int)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_score_stories_async(mock_db_path, mock_async_anthropic, monkeypatch):
    """Test scoring stories asynchronously."""
    # Create test stories
    from tests.fixtures.db_fixtures import create_test_stories, populate_test_db
    import sqlite3
    
    # Create unscored stories
    stories = []
    for i in range(5):
        stories.append({
            "id": 10000 + i,
            "title": f"Test Story {i}",
            "url": f"https://example.com/test-{i}",
            "score": 50,
            "by": "test_user",
            "time": int(datetime.now().timestamp()) - 3600,
            "type": "story",
            "timestamp": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        })
    
    # Connect to the database and add stories
    conn = sqlite3.connect(mock_db_path)
    conn.row_factory = sqlite3.Row
    
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
    
    # Insert stories
    for story in stories:
        cursor.execute('''
        INSERT INTO stories (
            id, title, url, score, by, time, timestamp, type, last_updated
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            story['id'],
            story['title'],
            story['url'],
            story['score'],
            story['by'],
            story['time'],
            story['timestamp'],
            story['type'],
            story['last_updated']
        ))
    
    conn.commit()
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        with patch('time.sleep'):  # Mock sleep to speed up test
            # Call the function
            scored_count = await score_stories_async(
                hours=24,
                min_score=10,
                batch_size=2
            )
    
    # Should have scored some stories
    assert scored_count > 0
    
    # Check database for scores
    cursor.execute('SELECT COUNT(*) FROM stories WHERE relevance_score IS NOT NULL')
    db_count = cursor.fetchone()[0]
    assert db_count == scored_count
    
    conn.close()


@pytest.mark.unit
def test_show_stories(mock_db_path, monkeypatch):
    """Test showing stories from the database."""
    # Create test stories with different qualities
    from tests.fixtures.db_fixtures import create_test_stories, populate_test_db
    import sqlite3
    
    conn = sqlite3.connect(mock_db_path)
    
    # Create stories with different qualities
    stories = [
        # High quality (high HN score, high relevance)
        {
            "id": 1,
            "title": "High Quality Story",
            "url": "https://example.com/high",
            "score": 100,
            "relevance_score": 90,
            "by": "user1",
            "time": int(datetime.now().timestamp()) - 3600,
            "timestamp": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "type": "story"
        },
        # Medium quality
        {
            "id": 2,
            "title": "Medium Quality Story",
            "url": "https://example.com/medium",
            "score": 50,
            "relevance_score": 70,
            "by": "user2",
            "time": int(datetime.now().timestamp()) - 7200,
            "timestamp": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "type": "story"
        },
        # Low quality (below threshold)
        {
            "id": 3,
            "title": "Low Quality Story",
            "url": "https://example.com/low",
            "score": 30,
            "relevance_score": 40,
            "by": "user3",
            "time": int(datetime.now().timestamp()) - 10800,
            "timestamp": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "type": "story"
        }
    ]
    
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
            story['relevance_score']
        ))
    
    conn.commit()
    conn.close()
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        # Test with default parameters
        count = show_stories()
        assert isinstance(count, int)  # Just check that it returns an integer
        
        # Test with lower thresholds
        count = show_stories(min_hn_score=10, min_relevance=30)
        assert isinstance(count, int)  # Just check that it returns an integer


@pytest.mark.unit
def test_cmd_fetch(monkeypatch):
    """Test the fetch command handler."""
    # Create mock args
    class MockArgs:
        hours = 24
        min_score = 30
        source = 'top'
        limit = 10
    
    # Mock asyncio.run to directly return a predefined result without using the coroutine
    mock_fetch = MagicMock(return_value=(5, 2))
    monkeypatch.setattr('src.main.fetch_stories_async', lambda *args, **kwargs: None)  # Placeholder
    monkeypatch.setattr('asyncio.run', lambda x: mock_fetch())
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        result = cmd_fetch(MockArgs())
    
    assert result == 0  # Should return success
    
    # Verify mock was called
    assert mock_fetch.called


@pytest.mark.unit
def test_cmd_score(monkeypatch):
    """Test the score command handler."""
    # Create mock args
    class MockArgs:
        hours = 24
        min_score = 30
        batch_size = 10
    
    # Mock score_stories_async to avoid actual scoring
    mock_score = MagicMock(return_value=7)
    monkeypatch.setattr('src.main.score_stories_async', lambda *args, **kwargs: None)  # Placeholder
    monkeypatch.setattr('asyncio.run', lambda x: mock_score())
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        result = cmd_score(MockArgs())
    
    assert result == 0  # Should return success
    
    # Verify mock was called
    assert mock_score.called


@pytest.mark.unit
def test_cmd_show(monkeypatch):
    """Test the show command handler."""
    # Create mock args
    class MockArgs:
        hours = 24
        min_score = 30
        min_relevance = 75
        hn_weight = 0.7
    
    # Mock show_stories to avoid database calls
    mock_show = MagicMock(return_value=5)
    monkeypatch.setattr('src.main.show_stories', mock_show)
    
    result = cmd_show(MockArgs())
    
    assert result == 0  # Should return success
    
    # Verify mock was called with correct args
    mock_show.assert_called_with(
        hours=24,
        min_hn_score=30,
        min_relevance=75,
        hn_weight=0.7
    )


@pytest.mark.unit
def test_main_no_command(monkeypatch):
    """Test main function with no command (should default to show)."""
    # Mock argparse to return args with no command
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value.command = None
    monkeypatch.setattr('argparse.ArgumentParser', lambda **kwargs: mock_parser)
    
    # Mock cmd_show to avoid actual command execution
    mock_show = MagicMock(return_value=0)
    monkeypatch.setattr('src.main.cmd_show', mock_show)
    
    # Mock init_db to avoid database initialization
    mock_init_db = MagicMock()
    monkeypatch.setattr('src.main.init_db', mock_init_db)
    
    result = main()
    
    assert result == 0
    assert mock_show.called


@pytest.mark.unit
def test_main_with_command(monkeypatch):
    """Test main function with a command."""
    # Mock argparse to return args with a command
    mock_parser = MagicMock()
    mock_args = MagicMock()
    mock_args.command = 'fetch'
    mock_args.func = MagicMock(return_value=0)
    mock_parser.parse_args.return_value = mock_args
    monkeypatch.setattr('argparse.ArgumentParser', lambda **kwargs: mock_parser)
    
    # Mock init_db to avoid database initialization
    mock_init_db = MagicMock()
    monkeypatch.setattr('src.main.init_db', mock_init_db)
    
    result = main()
    
    assert result == 0
    assert mock_args.func.called
    mock_args.func.assert_called_with(mock_args)


@pytest.mark.unit
def test_main_with_exception(monkeypatch):
    """Test main function handling an exception."""
    # Mock argparse to return args with a command that raises an exception
    mock_parser = MagicMock()
    mock_args = MagicMock()
    mock_args.command = 'fetch'
    mock_args.func = MagicMock(side_effect=Exception("Test error"))
    mock_parser.parse_args.return_value = mock_args
    monkeypatch.setattr('argparse.ArgumentParser', lambda **kwargs: mock_parser)
    
    # Mock init_db to avoid database initialization
    mock_init_db = MagicMock()
    monkeypatch.setattr('src.main.init_db', mock_init_db)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        result = main()
    
    assert result == 1  # Should return error


@pytest.mark.unit
def test_main_with_keyboard_interrupt(monkeypatch):
    """Test main function handling a keyboard interrupt."""
    # Mock argparse to return args with a command that raises KeyboardInterrupt
    mock_parser = MagicMock()
    mock_args = MagicMock()
    mock_args.command = 'fetch'
    mock_args.func = MagicMock(side_effect=KeyboardInterrupt())
    mock_parser.parse_args.return_value = mock_args
    monkeypatch.setattr('argparse.ArgumentParser', lambda **kwargs: mock_parser)
    
    # Mock init_db to avoid database initialization
    mock_init_db = MagicMock()
    monkeypatch.setattr('src.main.init_db', mock_init_db)
    
    # Mock print to avoid console output
    with patch('builtins.print'):
        result = main()
    
    assert result == 1  # Should return error