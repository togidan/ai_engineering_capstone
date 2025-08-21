#!/usr/bin/env python3
"""
Test database connection locally
"""
import os
import sys
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

print("🔍 Testing Database Connection")
print(f"DATABASE_URL exists: {bool(os.environ.get('DATABASE_URL'))}")
print(f"DATABASE_URL length: {len(os.environ.get('DATABASE_URL', ''))}")

# Test psycopg2 import
try:
    import psycopg2
    print("✅ psycopg2 import successful")
except ImportError as e:
    print(f"❌ psycopg2 import failed: {e}")
    sys.exit(1)

# Test connection
database_url = os.environ.get('DATABASE_URL')
if database_url:
    try:
        # Add SSL for Supabase
        if '?sslmode=' not in database_url:
            database_url += '?sslmode=require'
        
        print("🔌 Testing connection...")
        conn = psycopg2.connect(database_url)
        print("✅ PostgreSQL connection successful!")
        
        # Test a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"📊 PostgreSQL version: {version[0][:50]}...")
        
        conn.close()
        print("✅ Connection closed successfully")
        
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        sys.exit(1)
else:
    print("❌ No DATABASE_URL found in environment")

# Test database service
print("\n🗄️ Testing DatabaseService...")
try:
    from app.db import db_service
    print(f"Database type: {'PostgreSQL' if db_service.use_postgres else 'SQLite'}")
    
    if db_service.use_postgres:
        print("✅ DatabaseService is using PostgreSQL!")
    else:
        print("❌ DatabaseService is still using SQLite")
        
except Exception as e:
    print(f"❌ DatabaseService import failed: {e}")