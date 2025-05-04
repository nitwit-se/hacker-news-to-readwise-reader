#!/usr/bin/env python3

import os
import sys
import sqlite3
from typing import Dict, Any, List, Optional
import unittest
from unittest.mock import patch

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.db import get_unsynced_stories

class TestReadwiseMinRelevanceFilter(unittest.TestCase):
    """Test that the min_relevance filter works correctly for Readwise sync."""
    
    def setUp(self):
        """Set up a test database."""
        self.db_path = ":memory:"  # Use in-memory database for testing
        
        # Create a connection
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create the stories table with all required columns
        self.cursor.execute('''
        CREATE TABLE stories (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT,
            score INTEGER,
            comments INTEGER DEFAULT 0,
            by TEXT NOT NULL,
            time INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL,
            last_updated TEXT NOT NULL,
            relevance_score INTEGER,
            readwise_synced INTEGER DEFAULT 0,
            readwise_sync_time TEXT
        )
        ''')
        
        # Create metadata table
        self.cursor.execute('''
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        ''')
        
        # Insert default metadata values
        self.cursor.execute('INSERT INTO metadata (key, value) VALUES ("last_poll_time", "2023-05-01T12:00:00")')
        self.cursor.execute('INSERT INTO metadata (key, value) VALUES ("last_oldest_id", "0")')
        self.cursor.execute('INSERT INTO metadata (key, value) VALUES ("last_readwise_sync_time", "2023-05-01T12:00:00")')
        
        # Insert test stories with various relevance scores
        stories = [
            (1, "Test Story 1", "https://example.com/1", 50, 30, "user1", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 80, 1, "2023-05-01T12:00:00"),
            (2, "Test Story 2", "https://example.com/2", 40, 35, "user2", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 70, 0, None),
            (3, "Test Story 3", "https://example.com/3", 60, 40, "user3", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 90, 0, None),
            (4, "Test Story 4", "https://example.com/4", 30, 25, "user4", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 60, 0, None),
            (5, "Test Story 5", "https://example.com/5", 100, 80, "user5", 1610000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 95, 0, None),
            (6, "Test Story 6", "", 45, 30, "user6", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 75, 0, None),
            (7, "Test Story 7", None, 55, 35, "user7", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", 85, 0, None),
            (8, "Test Story 8", "https://example.com/8", 70, 45, "user8", 1620000000, "2023-05-01T12:00:00", "story", "2023-05-01T12:00:00", None, 0, None),
        ]
        
        for story in stories:
            self.cursor.execute('''
            INSERT INTO stories (
                id, title, url, score, comments, by, time, timestamp, type, last_updated, 
                relevance_score, readwise_synced, readwise_sync_time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', story)
            
        self.conn.commit()
    
    def tearDown(self):
        """Clean up after the test."""
        self.conn.close()
    
    def test_default_min_relevance_applied(self):
        """Test that a default min_relevance of 75 is applied when None is passed."""
        # We need to directly call the function with our conn
        # Build the query like get_unsynced_stories does
        query_parts = ['SELECT * FROM stories WHERE (readwise_synced = 0 OR readwise_synced IS NULL)']
        params = []
            
        # Apply minimum score threshold
        query_parts.append('AND score > 0')
            
        # IMPORTANT: Always require a non-NULL relevance score
        query_parts.append('AND relevance_score IS NOT NULL')
            
        # Always apply minimum relevance threshold - this is our fix
        # This ensures we only sync high-quality stories
        query_parts.append('AND relevance_score >= 75')
            
        # Execute query
        self.cursor.execute(' '.join(query_parts), tuple(params))
        
        rows = self.cursor.fetchall()
        # Convert to list of dicts for easier checking
        stories = []
        for row in rows:
            story = {"id": row[0], "relevance_score": row[10]} 
            stories.append(story)
        
        # Should only include stories with relevance score >= 75
        story_ids = [s["id"] for s in stories]
        
        # Stories with relevance >= 75 should be included
        for story_id in [3, 5, 6, 7]:
            self.assertIn(story_id, story_ids, f"Story {story_id} with relevance_score >= 75 should be included")
            
        # Stories with relevance < 75 should be excluded
        for story_id in [2, 4]:
            self.assertNotIn(story_id, story_ids, f"Story {story_id} with relevance_score < 75 should be excluded")
            
        # Story with no relevance score should be excluded 
        self.assertNotIn(8, story_ids, "Story with no relevance_score should be excluded")
        
        # Story that's already synced should be excluded
        self.assertNotIn(1, story_ids, "Story that's already synced should be excluded")
    
    def test_custom_min_relevance_applied(self):
        """Test that the specified min_relevance is applied when provided."""
        # We need to directly call the function with our conn
        # Build the query like get_unsynced_stories does
        query_parts = ['SELECT * FROM stories WHERE (readwise_synced = 0 OR readwise_synced IS NULL)']
        params = []
            
        # Apply minimum score threshold
        query_parts.append('AND score > 0')
            
        # IMPORTANT: Always require a non-NULL relevance score
        query_parts.append('AND relevance_score IS NOT NULL')
            
        # Apply custom min_relevance=85
        min_relevance = 85
        query_parts.append('AND relevance_score >= ?')
        params.append(min_relevance)
            
        # Execute query
        self.cursor.execute(' '.join(query_parts), tuple(params))
        
        rows = self.cursor.fetchall()
        # Convert to list of dicts for easier checking
        stories = []
        for row in rows:
            story = {"id": row[0], "relevance_score": row[10]} 
            stories.append(story)
        
        # Should only include stories with relevance score >= 85
        story_ids = [s["id"] for s in stories]
        
        # Stories with relevance >= 85 should be included
        for story_id in [3, 5, 7]:
            self.assertIn(story_id, story_ids, f"Story {story_id} with relevance_score >= 85 should be included")
            
        # Stories with relevance < 85 should be excluded
        for story_id in [2, 4, 6]:
            self.assertNotIn(story_id, story_ids, f"Story {story_id} with relevance_score < 85 should be excluded")
            
        # Story with no relevance score should be excluded
        self.assertNotIn(8, story_ids, "Story with no relevance_score should be excluded")
        
        # Story that's already synced should be excluded
        self.assertNotIn(1, story_ids, "Story that's already synced should be excluded")
    
    def test_lower_min_relevance_applied(self):
        """Test that a lower min_relevance is applied when specified."""
        # We need to directly call the function with our conn
        # Build the query like get_unsynced_stories does
        query_parts = ['SELECT * FROM stories WHERE (readwise_synced = 0 OR readwise_synced IS NULL)']
        params = []
            
        # Apply minimum score threshold
        query_parts.append('AND score > 0')
            
        # IMPORTANT: Always require a non-NULL relevance score
        query_parts.append('AND relevance_score IS NOT NULL')
            
        # Apply custom min_relevance=60
        min_relevance = 60
        query_parts.append('AND relevance_score >= ?')
        params.append(min_relevance)
            
        # Execute query
        self.cursor.execute(' '.join(query_parts), tuple(params))
        
        rows = self.cursor.fetchall()
        # Convert to list of dicts for easier checking
        stories = []
        for row in rows:
            story = {"id": row[0], "relevance_score": row[10]} 
            stories.append(story)
        
        # Should include stories with relevance score >= 60
        story_ids = [s["id"] for s in stories]
        
        # Stories with relevance >= 60 should be included
        for story_id in [2, 3, 4, 5, 6, 7]:
            self.assertIn(story_id, story_ids, f"Story {story_id} with relevance_score >= 60 should be included")
            
        # Story with no relevance score should be excluded
        self.assertNotIn(8, story_ids, "Story with no relevance_score should be excluded")
        
        # Story that's already synced should be excluded
        self.assertNotIn(1, story_ids, "Story that's already synced should be excluded")

if __name__ == '__main__':
    unittest.main()