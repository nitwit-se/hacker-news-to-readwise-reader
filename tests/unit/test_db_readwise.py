"""
Tests for the Readwise-related database functions.
"""

import os
import sqlite3
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.db import (
    init_db, get_unsynced_stories, mark_stories_as_synced,
    get_last_readwise_sync_time, update_last_readwise_sync_time,
    get_readwise_sync_stats
)

class TestReadwiseDbFunctions:
    """Test cases for Readwise-related database functions."""
    
    @pytest.fixture
    def setup_test_db(self, tmpdir):
        """Set up a temporary test database."""
        # Create a temporary database file
        db_path = os.path.join(tmpdir, "test_db.db")
        
        # Patch the DB_PATH constant to use our temporary file
        with patch("src.db.DB_PATH", db_path):
            # Initialize the database
            init_db()
            
            # Add the readwise_synced and readwise_sync_time columns if they don't exist
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if columns exist and add them if not
            cursor.execute("PRAGMA table_info(stories)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'readwise_synced' not in columns:
                cursor.execute("ALTER TABLE stories ADD COLUMN readwise_synced INTEGER DEFAULT 0")
            if 'readwise_sync_time' not in columns:
                cursor.execute("ALTER TABLE stories ADD COLUMN readwise_sync_time TEXT")
            if 'comments' not in columns:
                cursor.execute("ALTER TABLE stories ADD COLUMN comments INTEGER DEFAULT 0")
                
            conn.commit()
            
            # Set row factory for dictionaries
            conn.row_factory = sqlite3.Row
            
            # Add some test data
            current_time = datetime.now().isoformat()
            past_time = (datetime.now() - timedelta(hours=12)).timestamp()
            old_time = (datetime.now() - timedelta(hours=48)).timestamp()
            
            # Insert test stories with various sync states
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (1, "Test Story 1", "https://example.com/1", 50, 30, "user1", ?, ?, "story", ?, 80, 1, ?)
            ''', (int(past_time), current_time, current_time, current_time))
            
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (2, "Test Story 2", "https://example.com/2", 40, 35, "user2", ?, ?, "story", ?, 70, 0, NULL)
            ''', (int(past_time), current_time, current_time))
            
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (3, "Test Story 3", "https://example.com/3", 60, 40, "user3", ?, ?, "story", ?, 90, 0, NULL)
            ''', (int(past_time), current_time, current_time))
            
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (4, "Test Story 4", "https://example.com/4", 30, 25, "user4", ?, ?, "story", ?, 60, 0, NULL)
            ''', (int(past_time), current_time, current_time))
            
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (5, "Old Story", "https://example.com/5", 100, 80, "user5", ?, ?, "story", ?, 95, 0, NULL)
            ''', (int(old_time), current_time, current_time))
            
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (6, "Test Story 6", "", 45, 30, "user6", ?, ?, "story", ?, 75, 0, NULL)
            ''', (int(past_time), current_time, current_time))
            
            cursor.execute('''
            INSERT INTO stories (id, title, url, score, comments, by, time, timestamp, type, last_updated, relevance_score, readwise_synced, readwise_sync_time)
            VALUES (7, "Test Story 7", NULL, 55, 35, "user7", ?, ?, "story", ?, 85, 0, NULL)
            ''', (int(past_time), current_time, current_time))
            
            conn.commit()
            
            # Set initial metadata
            sync_time = datetime.now().isoformat()
            conn.execute('UPDATE metadata SET value = ? WHERE key = "last_readwise_sync_time"', (sync_time,))
            conn.commit()
            
            # Close the connection
            conn.close()
            
            yield db_path
    
    def test_get_unsynced_stories(self, setup_test_db):
        """Test getting unsynced stories with different filters."""
        with patch("src.db.DB_PATH", setup_test_db):
            # First, verify our test data is set up correctly
            conn = sqlite3.connect(setup_test_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM stories")
            total_stories = cursor.fetchone()[0]
            assert total_stories == 7  # Make sure we have all our test stories
            
            # Our main test: verify that min_relevance filter is always applied
            
            # Check if the comments column exists, and add it if it doesn't
            cursor.execute("PRAGMA table_info(stories)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'comments' not in columns:
                cursor.execute("ALTER TABLE stories ADD COLUMN comments INTEGER DEFAULT 30")
                conn.commit()
            
            # Test with no explicit min_relevance (should default to 75)
            stories = get_unsynced_stories(min_comments=0)  # Set min_comments=0 to match test data
            
            # All stories should have relevance >= 75 (per the default in get_unsynced_stories)
            for story in stories:
                assert story['relevance_score'] >= 75
                
            # Verify that stories with relevance < 75 are excluded
            story_ids = [s.get('id') for s in stories]
            assert 2 not in story_ids  # Story 2 has relevance 70
            assert 4 not in story_ids  # Story 4 has relevance 60
            
            # Test with explicit lower min_relevance
            stories = get_unsynced_stories(min_relevance=60, min_comments=0)  # Set min_comments=0 to match test data
            
            # Should include Story 4 (relevance 60) but not Story 2 (relevance 70)
            story_ids = [s.get('id') for s in stories]
            assert 4 in story_ids
            
            # Test with higher min_relevance 
            stories = get_unsynced_stories(min_relevance=80, min_comments=0)  # Set min_comments=0 to match test data
            
            # All stories should have relevance >= 80
            for story in stories:
                assert story['relevance_score'] >= 80
                
            # Stories with relevance < 80 should be excluded
            story_ids = [s.get('id') for s in stories]
            assert 2 not in story_ids  # relevance 70
            assert 4 not in story_ids  # relevance 60
            assert 6 not in story_ids  # relevance 75
            
            # Test with combined filters
            stories = get_unsynced_stories(hours=24, min_score=50, min_relevance=80, min_comments=0)  # Set min_comments=0 to match test data
            
            # Only stories matching all criteria should be returned
            story_ids = [s.get('id') for s in stories]
            assert 3 in story_ids  # Story 3: recent, score 60, relevance 90
            assert 7 in story_ids  # Story 7: recent, score 55, relevance 85
            assert 5 not in story_ids  # Story 5: not recent (48 hours old)
            assert 4 not in story_ids  # Story 4: score too low (30) and relevance too low (60) 
            assert 6 not in story_ids  # Story 6: score too low (45) and relevance too low (75)
    
    def test_mark_stories_as_synced(self, setup_test_db):
        """Test marking stories as synced."""
        with patch("src.db.DB_PATH", setup_test_db):
            # Mark stories 2, 3, and 4 as synced
            count = mark_stories_as_synced([2, 3, 4])
            assert count == 3
            
            # Check that they are now marked as synced
            # Note: Only stories with relevance score >= 75 will be returned (our default filter)
            stories = get_unsynced_stories()
            assert len(stories) == 3  # Stories 5, 6, and 7 remain unsynced (all have relevance_score >= 75)
            
            # Check the IDs of the remaining unsynced stories
            story_ids = [s.get('id') for s in stories]
            assert 2 not in story_ids
            assert 3 not in story_ids
            assert 4 not in story_ids
            assert 5 in story_ids
    
    def test_get_last_readwise_sync_time(self, setup_test_db):
        """Test getting the last Readwise sync time."""
        with patch("src.db.DB_PATH", setup_test_db):
            sync_time = get_last_readwise_sync_time()
            assert sync_time is not None
            
            # The sync time should be a valid ISO format string
            datetime.fromisoformat(sync_time)  # This will raise if invalid
    
    def test_update_last_readwise_sync_time(self, setup_test_db):
        """Test updating the last Readwise sync time."""
        with patch("src.db.DB_PATH", setup_test_db):
            # Get the current sync time
            old_sync_time = get_last_readwise_sync_time()
            
            # Update the sync time
            new_sync_time = update_last_readwise_sync_time()
            
            # Check that the sync time was updated
            assert new_sync_time != old_sync_time
            
            # Check that the updated sync time is returned by get_last_readwise_sync_time
            current_sync_time = get_last_readwise_sync_time()
            assert current_sync_time == new_sync_time
    
    def test_get_readwise_sync_stats(self, setup_test_db):
        """Test getting Readwise sync statistics."""
        with patch("src.db.DB_PATH", setup_test_db):
            stats = get_readwise_sync_stats()
            
            # Check the stats
            assert stats['total_stories'] == 7
            assert stats['synced_stories'] == 1  # Only story 1 is synced
            assert stats['unsynced_stories'] == 6
            assert stats['last_sync_time'] is not None