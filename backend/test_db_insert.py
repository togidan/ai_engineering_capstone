#!/usr/bin/env python3
"""
Test script to verify database insertion is working
"""
import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("Testing Database Insertion")
print(f"DATABASE_URL exists: {bool(os.environ.get('DATABASE_URL'))}")
print(f"DATABASE_URL length: {len(os.environ.get('DATABASE_URL', ''))}")

# Test database service
try:
    from app.db import db_service
    print(f"\nDatabase type: {'PostgreSQL' if db_service.use_postgres else 'SQLite'}")
    
    if db_service.use_postgres:
        print("SUCCESS: Using PostgreSQL (Supabase)")
    else:
        print("ERROR: Still using SQLite - this is the problem!")
        
    # Test getting stats
    stats = db_service.get_database_stats()
    print(f"Current stats: {stats}")
    
    # Test database name to verify which database we're connected to
    print("\nTesting database connection details...")
    try:
        with db_service._get_connection() as conn:
            if db_service.use_postgres:
                cursor = conn.cursor()
                cursor.execute("SELECT current_database();")
                db_name = cursor.fetchone()[0]
                print(f"Connected to PostgreSQL database: {db_name}")
                
                # Check PostgreSQL host
                if hasattr(db_service, 'postgres_url') and db_service.postgres_url:
                    url_parts = db_service.postgres_url.split('@')
                    if len(url_parts) > 1:
                        print(f"PostgreSQL host: {url_parts[1].split('?')[0]}")
            else:
                print(f"Connected to SQLite database: {db_service.db_path}")
    except Exception as e:
        print(f"Could not verify database details: {e}")
    
    # Test inserting a simple document
    print("\nTesting document insertion...")
    doc_id = db_service.insert_document(
        path="/test/simple_test.txt",
        name="Test Document", 
        file_size=100,
        description="A simple test document"
    )
    
    if doc_id:
        print(f"SUCCESS: Test document inserted with ID: {doc_id}")
        
        # Test inserting chunks
        print("Testing chunk insertion...")
        test_chunks = ["This is chunk 1", "This is chunk 2", "This is chunk 3"]
        chunk_ids = db_service.insert_chunks(doc_id, test_chunks)
        
        if chunk_ids:
            print(f"SUCCESS: Test chunks inserted with IDs: {chunk_ids}")
            
            # Get updated stats
            updated_stats = db_service.get_database_stats()
            print(f"Updated stats: {updated_stats}")
        else:
            print("ERROR: Failed to insert test chunks")
    else:
        print("ERROR: Failed to insert test document")
        
except Exception as e:
    print(f"ERROR: Test failed: {e}")
    import traceback
    traceback.print_exc()