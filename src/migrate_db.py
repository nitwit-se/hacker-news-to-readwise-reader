#!/usr/bin/env python3

import sqlite3
import os
from src.db import DB_PATH

def migrate_database():
    """Add content columns to existing stories table if they don't exist."""
    print(f"Checking database at {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if the columns already exist
    cursor.execute("PRAGMA table_info(stories)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Add content column if it doesn't exist
    if 'content' not in columns:
        print("Adding 'content' column to stories table...")
        cursor.execute('ALTER TABLE stories ADD COLUMN content TEXT')
    
    # Add content_fetched column if it doesn't exist
    if 'content_fetched' not in columns:
        print("Adding 'content_fetched' column to stories table...")
        cursor.execute('ALTER TABLE stories ADD COLUMN content_fetched INTEGER DEFAULT 0')
    
    conn.commit()
    conn.close()
    
    print("Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()