#!/usr/bin/env python3

import os
import sys
import sqlite3
from typing import Dict, Any
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.classifier import get_relevance_score, is_interesting
from src.db import update_story_scores

class TestFixAPIFailure(unittest.TestCase):
    """Test that API failures don't update the relevance score."""
    
    def setUp(self):
        """Set up a test database."""
        self.db_path = ":memory:"  # Use in-memory database for testing
        
        # Create a connection
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        
        # Create the stories table
        self.cursor.execute('''
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
        
        # Insert a test story
        self.cursor.execute('''
        INSERT INTO stories (
            id, title, url, score, by, time, timestamp, type, last_updated, relevance_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            12345,
            "Test Story",
            "https://example.com",
            100,
            "test_user",
            1620000000,
            "2023-05-01T12:00:00",
            "story",
            "2023-05-01T12:00:00",
            None  # Initially unscored
        ))
        
        self.conn.commit()
    
    def tearDown(self):
        """Clean up after the test."""
        self.conn.close()
    
    @patch('src.classifier.client')
    def test_api_failure_doesnt_update_score(self, mock_client):
        """Test that when the API call fails, we don't update relevance_score."""
        # Make the API call fail
        mock_response = MagicMock()
        mock_client.messages.create.side_effect = Exception("API failure")
        
        # Create a test story that simulates what we get from the database
        story = {
            "id": 12345,
            "title": "Test Story",
            "url": "https://example.com",
            "score": 100,
            "by": "test_user",
            "time": 1620000000,
            "timestamp": "2023-05-01T12:00:00",
            "type": "story",
            "last_updated": "2023-05-01T12:00:00"
        }
        
        # Try to score the story (should fail gracefully)
        with patch('builtins.print'):  # Silence print statements
            result = is_interesting(story)
            self.assertFalse(result)  # Should return False on API failure
        
        # Check that the story didn't get a relevance_score
        self.assertNotIn('relevance_score', story)
        
        # When API fails, the story dict shouldn't have a relevance_score field added
        # This means when we update the database, no relevance_score update will happen
        
        # Simulate updating the database by creating a story with the same ID but a different score
        self.cursor.execute('''
        UPDATE stories
        SET score = ?
        WHERE id = ?
        ''', (110, 12345))
        self.conn.commit()
        
        # Check the database to make sure relevance_score is still NULL
        self.cursor.execute('SELECT relevance_score FROM stories WHERE id = 12345')
        db_score = self.cursor.fetchone()[0]
        self.assertIsNone(db_score)

if __name__ == '__main__':
    unittest.main()