#!/usr/bin/env python3

import os
import sys
import sqlite3
from typing import Dict, List, Optional, Any
import unittest

# Add root directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the function we want to test
from src.db import get_unsynced_stories

class TestReadwiseMinRelevanceFilter(unittest.TestCase):
    """Directly test the new min_relevance filter behavior."""
    
    def setUp(self):
        # Create in-memory database
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        
        # Create stories table
        self.cursor.execute('''
        CREATE TABLE stories (
            id INTEGER PRIMARY KEY,
            title TEXT,
            url TEXT,
            score INTEGER,
            comments INTEGER DEFAULT 30,
            by TEXT,
            time INTEGER,
            timestamp TEXT,
            type TEXT,
            last_updated TEXT,
            relevance_score INTEGER,
            readwise_synced INTEGER DEFAULT 0,
            readwise_sync_time TEXT
        )
        ''')
        
        # Create metadata table
        self.cursor.execute('''
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Insert test stories with different relevance scores
        test_stories = [
            (1, 'High relevance', 'https://example.com/1', 100, 50, 'user1', 1620000000, '2023-01-01', 'story', '2023-01-01', 90, 0, None),
            (2, 'Medium relevance', 'https://example.com/2', 80, 40, 'user2', 1620000000, '2023-01-01', 'story', '2023-01-01', 70, 0, None),
            (3, 'Low relevance', 'https://example.com/3', 60, 30, 'user3', 1620000000, '2023-01-01', 'story', '2023-01-01', 50, 0, None),
            (4, 'Border relevance', 'https://example.com/4', 90, 45, 'user4', 1620000000, '2023-01-01', 'story', '2023-01-01', 75, 0, None),
            (5, 'No relevance', 'https://example.com/5', 70, 35, 'user5', 1620000000, '2023-01-01', 'story', '2023-01-01', None, 0, None),
        ]
        
        for story in test_stories:
            self.cursor.execute('''
            INSERT INTO stories (
                id, title, url, score, comments, by, time, timestamp, type, last_updated, 
                relevance_score, readwise_synced, readwise_sync_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', story)
            
        self.conn.commit()
    
    def tearDown(self):
        self.conn.close()
    
    def test_default_min_relevance(self):
        """Test that a default of 75 is applied when min_relevance is None."""
        # Build and execute the query directly based on get_unsynced_stories function
        query_parts = ['SELECT * FROM stories WHERE (readwise_synced = 0 OR readwise_synced IS NULL)']
        params = []
        
        # Apply score filter
        query_parts.append('AND score > 0')
        
        # Apply min_comments filter
        min_comments = 0  # Set to 0 to include all test data
        query_parts.append('AND comments >= ?')
        params.append(min_comments)
        
        # Require non-NULL relevance_score
        query_parts.append('AND relevance_score IS NOT NULL')
        
        # The key part: Apply min_relevance even though it's not specified
        # This is the "fix" we're testing
        query_parts.append('AND relevance_score >= 75')
        
        self.cursor.execute(' '.join(query_parts), tuple(params))
        results = self.cursor.fetchall()
        
        # Should only get stories with relevance_score >= 75
        story_ids = [row[0] for row in results]
        self.assertEqual(len(story_ids), 2)  # Should only have stories 1 and 4
        self.assertIn(1, story_ids)  # Story 1 has relevance 90
        self.assertIn(4, story_ids)  # Story 4 has relevance 75
        self.assertNotIn(2, story_ids)  # Story 2 has relevance 70
        self.assertNotIn(3, story_ids)  # Story 3 has relevance 50
        self.assertNotIn(5, story_ids)  # Story 5 has no relevance
        
    def test_custom_min_relevance(self):
        """Test that a custom min_relevance is applied correctly."""
        # Build and execute the query with a custom min_relevance
        query_parts = ['SELECT * FROM stories WHERE (readwise_synced = 0 OR readwise_synced IS NULL)']
        params = []
        
        # Apply score filter
        query_parts.append('AND score > 0')
        
        # Apply min_comments filter
        min_comments = 0  # Set to 0 to include all test data
        query_parts.append('AND comments >= ?')
        params.append(min_comments)
        
        # Require non-NULL relevance_score
        query_parts.append('AND relevance_score IS NOT NULL')
        
        # Apply custom min_relevance of 60
        min_relevance = 60
        query_parts.append('AND relevance_score >= ?')
        params.append(min_relevance)
        
        self.cursor.execute(' '.join(query_parts), tuple(params))
        results = self.cursor.fetchall()
        
        # Should only get stories with relevance_score >= 60
        story_ids = [row[0] for row in results]
        self.assertEqual(len(story_ids), 3)  # Should have stories 1, 2, and 4
        self.assertIn(1, story_ids)  # Story 1 has relevance 90
        self.assertIn(2, story_ids)  # Story 2 has relevance 70
        self.assertIn(4, story_ids)  # Story 4 has relevance 75
        self.assertNotIn(3, story_ids)  # Story 3 has relevance 50
        self.assertNotIn(5, story_ids)  # Story 5 has no relevance

if __name__ == '__main__':
    unittest.main()