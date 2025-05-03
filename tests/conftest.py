"""
Global test fixtures for the hackernews-poller project.
"""

import os
import sys
import pytest
import sqlite3
import tempfile
from typing import Iterator, Dict, Any, List, Tuple, Optional

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.db
from src.db import init_db

# Import aioresponses for async tests
try:
    from aioresponses import aioresponses as aioresponses_cls
    
    @pytest.fixture
    def aioresponses():
        """Fixture that provides a mock response object for aiohttp."""
        with aioresponses_cls() as m:
            yield m
except ImportError:
    # This allows tests to run even if aioresponses is not installed
    pass


@pytest.fixture
def sample_story() -> Dict[str, Any]:
    """
    Returns a sample Hacker News story dict.
    """
    return {
        "id": 39428394,
        "title": "Test Story Title",
        "url": "https://example.com/test-story",
        "score": 42,
        "by": "test_user",
        "time": 1683123456,  # Unix timestamp
        "type": "story",
        "kids": [123456, 123457],  # Comment IDs
        "descendants": 2,
    }


@pytest.fixture
def sample_stories() -> List[Dict[str, Any]]:
    """
    Returns a list of sample Hacker News stories.
    """
    return [
        {
            "id": 39428394,
            "title": "Test Story 1",
            "url": "https://example.com/test-story-1",
            "score": 42,
            "by": "test_user",
            "time": 1683123456,
            "type": "story",
        },
        {
            "id": 39428395,
            "title": "Test Story 2",
            "url": "https://example.com/test-story-2",
            "score": 100,
            "by": "test_user2",
            "time": 1683123457,
            "type": "story",
        },
        {
            "id": 39428396,
            "title": "Test Story 3",
            "url": "https://example.com/test-story-3",
            "score": 10,
            "by": "test_user3",
            "time": 1683123458,
            "type": "story",
        },
    ]


@pytest.fixture
def mock_db_path() -> Iterator[str]:
    """
    Creates a temporary SQLite database file for testing.
    The database is removed after the test is completed.
    """
    # Create a temporary file for the database
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    
    # Override the DB_PATH in the src.db module
    original_db_path = src.db.DB_PATH
    src.db.DB_PATH = db_path
    
    # Initialize the test database
    init_db()
    
    # Provide the db_path to the test
    yield db_path
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)
    
    # Restore the original DB_PATH
    src.db.DB_PATH = original_db_path


@pytest.fixture
def mock_anthropic_api_key(monkeypatch) -> None:
    """
    Set a mock ANTHROPIC_API_KEY environment variable for testing.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "mock-api-key-for-testing")