#!/usr/bin/env python3
"""
Initialize Knowledge Base - SQLite database and Milvus collection
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from app.db import db_service
from app.milvus_utils import milvus_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Initialize both SQLite database and Milvus collection"""
    
    logger.info("🚀 Starting Knowledge Base initialization...")
    
    success = True
    
    # 1. Initialize SQLite database
    logger.info("📁 Initializing SQLite database...")
    try:
        # Database is automatically initialized when db_service is imported
        stats = db_service.get_database_stats()
        logger.info(f"✅ SQLite database ready: {stats}")
    except Exception as e:
        logger.error(f"❌ SQLite initialization failed: {e}")
        success = False
    
    # 2. Initialize Milvus collection
    logger.info("🔍 Initializing Milvus collection...")
    try:
        if not milvus_service.is_available():
            logger.warning("⚠️  Milvus not available - check environment variables")
            success = False
        else:
            # Create collection if needed
            if milvus_service.collection is None:
                collection_success = milvus_service.create_collection()
                if not collection_success:
                    logger.error("❌ Failed to create Milvus collection")
                    success = False
                else:
                    logger.info("✅ Milvus collection created")
            else:
                logger.info("✅ Milvus collection already exists")
            
            # Load collection
            milvus_service.load_collection()
            
            # Get stats
            milvus_stats = milvus_service.get_collection_stats()
            logger.info(f"📊 Milvus stats: {milvus_stats}")
            
    except Exception as e:
        logger.error(f"❌ Milvus initialization failed: {e}")
        success = False
    
    # 3. Summary
    if success:
        logger.info("🎉 Knowledge Base initialization completed successfully!")
        logger.info("💡 Next steps:")
        logger.info("   - Run 'python scripts/ingest_wiki.py' to bootstrap with Wikipedia data")
        logger.info("   - Start the API server with 'uvicorn app.main:app --reload'")
    else:
        logger.error("💥 Knowledge Base initialization failed!")
        logger.error("🔧 Check your environment variables:")
        logger.error("   - MILVUS_URI: Milvus connection URI")
        logger.error("   - MILVUS_TOKEN: Milvus authentication token")
        logger.error("   - OPENAI_API_KEY: OpenAI API key for embeddings")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)