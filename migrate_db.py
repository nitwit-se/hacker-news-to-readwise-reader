#!/usr/bin/env python3

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hn_stories.db')

def migrate_database():
    """Migrate the database to remove content-related fields."""
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print("Database file not found. No migration needed.")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if stories table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stories'")
    if not cursor.fetchone():
        print("Stories table not found. No migration needed.")
        conn.close()
        return False
    
    # Check if the content-related columns exist
    cursor.execute("PRAGMA table_info(stories)")
    columns = [col[1] for col in cursor.fetchall()]
    
    content_columns = [
        'content', 
        'content_fetched', 
        'error_type', 
        'error_message', 
        'error_status', 
        'last_fetch_attempt'
    ]
    
    # Check if any content columns exist
    migration_needed = any(col in columns for col in content_columns)
    
    if not migration_needed:
        print("No content-related columns found. No migration needed.")
        conn.close()
        return False
    
    print("Starting database migration to remove content-related fields...")
    
    try:
        # Create a new table without the content-related columns
        cursor.execute('''
        CREATE TABLE stories_new (
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
        
        # Copy data from old table to new table
        cursor.execute('''
        INSERT INTO stories_new (id, title, url, score, by, time, timestamp, type)
        SELECT id, title, url, score, by, time, timestamp, type FROM stories
        ''')
        
        # Drop the old table
        cursor.execute('DROP TABLE stories')
        
        # Rename the new table to stories
        cursor.execute('ALTER TABLE stories_new RENAME TO stories')
        
        # Commit the changes
        conn.commit()
        print("Migration successful!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        conn.close()
        return False
    
    conn.close()
    return True

if __name__ == '__main__':
    print("Hacker News Poller Database Migration")
    print("-------------------------------------")
    print("This script will remove content-related fields from the database.")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        force = True
    else:
        response = input("Do you want to proceed? (y/n): ")
        force = response.lower() in ('y', 'yes')
    
    if force:
        success = migrate_database()
        if success:
            print("Database migration completed successfully.")
        else:
            print("Database migration was not performed or encountered an error.")
    else:
        print("Migration cancelled.")