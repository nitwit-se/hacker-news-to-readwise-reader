#!/usr/bin/env python3
"""
Script to clean the Hacker News database by removing all rows from all tables.
This preserves the table structure but removes all data for fresh testing.
"""

import sqlite3
import os
from src.db import DB_PATH

def clean_database() -> None:
    """Clean the database by removing all rows from all tables."""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    # Delete all rows from each table
    for table in tables:
        table_name = table[0]
        if table_name != 'sqlite_sequence':  # Skip internal SQLite tables
            print(f"Cleaning table: {table_name}")
            cursor.execute(f"DELETE FROM {table_name}")
    
    # Reset metadata values with current timestamp
    from datetime import datetime
    current_time = datetime.now().isoformat()
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_poll_time', ?)", 
                  (current_time,))
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_oldest_id', '0')")
    cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_readwise_sync_time', ?)", 
                  (current_time,))
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print("Database cleaned successfully")

if __name__ == "__main__":
    clean_database()