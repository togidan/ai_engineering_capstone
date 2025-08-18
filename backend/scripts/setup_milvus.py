#!/usr/bin/env python3
"""
Setup script for Milvus collection initialization
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from app.milvus_utils import milvus_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Initialize Milvus collection for knowledge base"""
    
    logger.info("Starting Milvus setup...")
    
    # Check if Milvus service is available
    if not milvus_service.is_available():
        logger.error("Milvus service not available. Check environment variables:")
        logger.error("- MILVUS_URI: Milvus connection URI")
        logger.error("- MILVUS_TOKEN: Milvus authentication token") 
        logger.error("- OPENAI_API_KEY: OpenAI API key for embeddings")
        return False
    
    # Create collection if it doesn't exist
    try:
        if milvus_service.collection is None:
            logger.info("Creating Milvus collection...")
            success = milvus_service.create_collection()
            
            if success:
                logger.info("✅ Milvus collection created successfully")
            else:
                logger.error("❌ Failed to create Milvus collection")
                return False
        else:
            logger.info("✅ Milvus collection already exists")
        
        # Load collection into memory
        milvus_service.load_collection()
        logger.info("✅ Collection loaded into memory")
        
        # Get collection stats
        stats = milvus_service.get_collection_stats()
        logger.info(f"📊 Collection stats: {stats}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Milvus setup failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)