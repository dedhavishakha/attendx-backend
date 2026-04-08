#!/usr/bin/env python3
"""
View Database Tables - Simple script to display all database tables
Usage: python view_database.py
"""

import sqlite3
import os
import sys

db_path = r"C:\Users\Vishakha Dedha\Desktop\chromeextensions\new1\database.py"

print("\n" + "="*100)
print("📊 ATTENDX DATABASE VIEWER")
print("="*100)

if not os.path.exists(db_path):
    print(f"\n❌ ERROR: Database not found at:\n   {db_path}")
    print("\nPlease make sure:")
    print("  1. Flask has been run at least once")
    print("  2. The path is correct")
    sys.exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = cursor.fetchall()

    if not tables:
        print("\n❌ No tables found in database!")
        sys.exit(1)

    for table in tables:
        table_name = table[0]
        
        # Skip sqlite internal tables
        if table_name.startswith('sqlite_'):
            continue
        
        print(f"\n\n{'='*100}")
        print(f"📋 TABLE: {table_name.upper()}")
        print(f"{'='*100}\n")
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        if not columns:
            print(f"(No columns)")
            continue
        
        col_names = [col[1] for col in columns]
        col_widths = [max(len(name), 15) for name in col_names]
        
        # Print header
        header = " | ".join(f"{name:<{width}}" for name, width in zip(col_names, col_widths))
        print(header)
        print("-" * len(header))
        
        # Get all data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 100")
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                line = " | ".join(
                    f"{str(cell):<{width}}" 
                    for cell, width in zip(row, col_widths)
                )
                print(line)
            
            # Check if there are more rows
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\n✅ Total records: {count}")
        else:
            print("(No data)")

    conn.close()
    
    print("\n" + "="*100)
    print("✅ Database view complete!")
    print("="*100 + "\n")

except sqlite3.Error as e:
    print(f"\n❌ Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)