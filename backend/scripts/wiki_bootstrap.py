#!/usr/bin/env python3
"""
Bootstrap Knowledge Base with Wikipedia data for US cities
Uses the KB upload endpoint to chunk and embed Wikipedia content
"""

import os
import sys
import logging
import time
import requests
import io
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Force Postgres for bootstrap to avoid SQLite fallback when DATABASE_URL is set
if os.getenv('DATABASE_URL') and os.getenv('FORCE_POSTGRES') != '1':
    os.environ['FORCE_POSTGRES'] = '1'

# Import database services at module level (like test script)
from app.db import db_service
from app.milvus_utils import milvus_service  
from app.text_utils import text_processor

try:
    import wikipedia
except ImportError:
    print("Installing wikipedia package...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "wikipedia"])
    import wikipedia

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Major US cities for economic development analysis
CITIES = [
    "Columbus, Ohio", "Cleveland, Ohio", "Cincinnati, Ohio",
    "Austin, Texas", "Dallas, Texas", "Houston, Texas",
    "Denver", "Colorado Springs, Colorado", 
    "Atlanta, Georgia", "Nashville, Tennessee",
    "Seattle, Washington", "Portland, Oregon",
    "Phoenix, Arizona", "Tucson, Arizona",
    "Charlotte, North Carolina", "Raleigh, North Carolina",
    "Indianapolis, Indiana", "Detroit, Michigan",
    "Milwaukee, Wisconsin", "Kansas City, Missouri",
    "Oklahoma City, Oklahoma", "Tulsa, Oklahoma",
    "Las Vegas, Nevada", "Sacramento, California",
    "San Diego, California", "San Jose, California"
]

# API endpoint - use environment variable or default to localhost
API_BASE = os.environ.get('API_URL', 'http://localhost:8000')

class WikiBootstrapper:
    def __init__(self):
        self.total_documents = 0
        self.total_chunks = 0
        self.failed_cities = []
        wikipedia.set_rate_limiting(True)
        
    def get_city_content(self, city_name: str) -> tuple[str, str]:
        """Get Wikipedia content for a city"""
        try:
            logger.info(f"🏙️  Fetching Wikipedia data for {city_name}...")
            
            # Search for the city page
            search_results = wikipedia.search(city_name, results=3)
            if not search_results:
                logger.warning(f"❌ No Wikipedia results for {city_name}")
                return None, None
            
            # Try to get the main city page
            page_title = search_results[0]
            try:
                page = wikipedia.page(page_title)
            except wikipedia.exceptions.DisambiguationError as e:
                # Try the first option from disambiguation
                if e.options:
                    page = wikipedia.page(e.options[0])
                else:
                    logger.warning(f"❌ Disambiguation error for {city_name}")
                    return None, None
            except wikipedia.exceptions.PageError:
                logger.warning(f"❌ Page not found for {city_name}")
                return None, None
            
            # Filter content for economic development relevance
            content = self.filter_economic_content(page.content, city_name)
            
            if len(content) < 1000:
                logger.warning(f"⚠️  Content too short for {city_name}")
                return None, None
                
            return content, page.url
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch content for {city_name}: {e}")
            return None, None
    
    def filter_economic_content(self, content: str, city_name: str) -> str:
        """Filter content to focus on economic development topics"""
        lines = content.split('\n')
        filtered_lines = []
        current_section = ""
        include_section = False
        
        # Economic development keywords
        econ_keywords = [
            'economy', 'economic', 'business', 'industry', 'industrial', 'manufacturing',
            'technology', 'biotech', 'aerospace', 'logistics', 'transportation', 'infrastructure',
            'workforce', 'employment', 'jobs', 'unemployment', 'education', 'university',
            'research', 'development', 'demographics', 'population', 'income', 'commerce',
            'trade', 'export', 'import', 'port', 'airport', 'railroad', 'highway',
            'utilities', 'power', 'energy', 'water', 'telecommunications', 'broadband'
        ]
        
        for line in lines:
            # Check if this is a section header
            if line.startswith('='):
                current_section = line.lower()
                # Include section if it contains economic keywords
                include_section = any(keyword in current_section for keyword in econ_keywords)
                if include_section:
                    filtered_lines.append(line)
            elif include_section:
                # Include content from relevant sections
                filtered_lines.append(line)
            elif any(keyword in line.lower() for keyword in econ_keywords):
                # Include individual lines that mention economic topics
                filtered_lines.append(line)
        
        # If filtered content is too short, include more general content
        filtered_content = '\n'.join(filtered_lines)
        if len(filtered_content) < 1000:
            # Take first 3000 characters of original content
            filtered_content = content[:3000]
        
        return filtered_content
    
    def upload_to_kb(self, city_name: str, content: str, source_url: str) -> bool:
        """Upload content directly to database"""
        try:
            
            # Create document content
            file_content = f"# {city_name} Economic Development Profile\n\n"
            file_content += f"Source: Wikipedia - {source_url}\n\n"
            file_content += content
            
            # Extract metadata
            auto_metadata = text_processor.extract_metadata(file_content, f"{city_name}_econ_profile")
            logger.info(f"   📝 Generated metadata: {auto_metadata.get('summary', 'No summary')[:100]}...")
            
            # Insert document into database
            logger.info(f"   💾 Inserting document for {city_name}...")
            doc_id = db_service.insert_document(
                path=f"/virtual/{city_name.replace(', ', '_')}_econ_profile.txt",
                name=f"{city_name} Economic Development Profile",
                file_size=len(file_content.encode('utf-8')),
                description=auto_metadata["summary"]
            )
            logger.info(f"   📄 Document inserted with ID: {doc_id}")
            
            if doc_id:
                # Generate chunks
                chunks = text_processor.chunk_text(file_content)
                
                if chunks:
                    logger.info(f"   🔢 Generated {len(chunks)} chunks")
                    # Insert chunks
                    chunk_ids = db_service.insert_chunks(doc_id, chunks)
                    logger.info(f"   📦 Inserted chunks with IDs: {chunk_ids[:3] if chunk_ids else 'None'}...")
                    
                    if chunk_ids:
                        # Prepare data for Milvus insertion
                        chunks_data = []
                        for chunk_id, chunk_text in zip(chunk_ids, chunks):
                            chunks_data.append({
                                "primary_key": chunk_id,
                                "text": chunk_text,
                                "jurisdiction": city_name,
                                "industry": "economic_development",
                                "doc_type": "city_profile"
                            })
                        
                        # Insert into Milvus
                        if milvus_service.is_available():
                            pks = milvus_service.insert_chunks(chunks_data)
                            if pks:
                                # Update chunk records with correct Milvus primary keys
                                for chunk_id, pk in zip(chunk_ids, pks):
                                    db_service.update_chunk_milvus_pk(chunk_id, int(pk))
                        
                        self.total_documents += 1
                        self.total_chunks += len(chunks)
                        logger.info(f"   ✅ Uploaded: {len(chunks)} chunks")
                        return True
                    else:
                        logger.error(f"   ❌ Failed to insert chunks for {city_name}")
                        return False
                else:
                    logger.error(f"   ❌ No chunks generated for {city_name}")
                    return False
            else:
                logger.error(f"   ❌ Failed to insert document for {city_name}")
                return False
                
        except Exception as e:
            logger.error(f"   ❌ Upload error for {city_name}: {e}")
            return False
    
    def bootstrap_city(self, city_name: str):
        """Process a single city"""
        try:
            # Get Wikipedia content
            content, source_url = self.get_city_content(city_name)
            if not content:
                self.failed_cities.append(city_name)
                return
            
            # Upload to knowledge base
            success = self.upload_to_kb(city_name, content, source_url)
            if not success:
                self.failed_cities.append(city_name)
                return
                
            logger.info(f"✅ {city_name} completed successfully")
            
            # Rate limiting - be nice to Wikipedia and our API
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Failed to process {city_name}: {e}")
            self.failed_cities.append(city_name)

def main():
    """Main bootstrap process"""
    logger.info("🌐 Starting Wikipedia bootstrap for Knowledge Base...")
    logger.info(f"📋 Processing {len(CITIES)} cities for economic development data")
    
    # Test database connectivity
    try:
        
        # Log database configuration details
        logger.info(f"🔍 Database service using PostgreSQL: {db_service.use_postgres}")
        if hasattr(db_service, 'postgres_url'):
            logger.info(f"🔍 PostgreSQL URL configured: {bool(db_service.postgres_url)}")
            if db_service.postgres_url:
                # Log partial URL for debugging (without sensitive info)
                url_parts = db_service.postgres_url.split('@')
                if len(url_parts) > 1:
                    logger.info(f"🔍 PostgreSQL host: {url_parts[1].split('?')[0]}")
        
        # Test database connection
        stats = db_service.get_database_stats()
        if "error" in stats:
            logger.error(f"❌ Database connection failed: {stats['error']}")
            return False
        
        logger.info("✅ Database connectivity confirmed")
        logger.info(f"📊 Current DB stats: {stats}")
        
        # Test a simple query to verify we're connected to the right database
        try:
            with db_service._get_connection() as conn:
                if db_service.use_postgres:
                    cursor = conn.cursor()
                    cursor.execute("SELECT current_database();")
                    db_name = cursor.fetchone()[0]
                    logger.info(f"🗄️ Connected to PostgreSQL database: {db_name}")
                else:
                    logger.info(f"🗄️ Connected to SQLite database: {db_service.db_path}")
        except Exception as e:
            logger.warning(f"Could not verify database name: {e}")
        
        # Test Milvus availability
        if milvus_service.is_available():
            logger.info("✅ Milvus service available")
        else:
            logger.warning("⚠️ Milvus service not available - chunks won't be indexed for search")
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error(f"❌ Exception details: {type(e).__name__}: {str(e)}")
        return False
    
    bootstrapper = WikiBootstrapper()
    
    # Process each city
    start_time = time.time()
    for i, city in enumerate(CITIES, 1):
        logger.info(f"📍 [{i}/{len(CITIES)}] Processing {city}...")
        bootstrapper.bootstrap_city(city)
        
        # Progress update
        if i % 5 == 0:
            elapsed = time.time() - start_time
            logger.info(f"⏱️  Progress: {i}/{len(CITIES)} cities, "
                       f"{bootstrapper.total_documents} docs, "
                       f"{bootstrapper.total_chunks} chunks, "
                       f"{elapsed:.1f}s elapsed")
    
    # Final summary
    elapsed = time.time() - start_time
    logger.info(f"🎉 Wikipedia bootstrap completed!")
    logger.info(f"📊 Summary:")
    logger.info(f"   - Documents created: {bootstrapper.total_documents}")
    logger.info(f"   - Total chunks: {bootstrapper.total_chunks}")
    logger.info(f"   - Cities processed: {len(CITIES) - len(bootstrapper.failed_cities)}")
    logger.info(f"   - Failed cities: {len(bootstrapper.failed_cities)}")
    logger.info(f"   - Total time: {elapsed:.1f} seconds")
    
    if bootstrapper.failed_cities:
        logger.warning(f"⚠️  Failed cities: {', '.join(bootstrapper.failed_cities)}")
    
    # Check if we have sufficient data
    if bootstrapper.total_chunks >= 1000:
        logger.info("✅ Target of ≥1000 chunks achieved!")
    else:
        logger.warning(f"⚠️  Only {bootstrapper.total_chunks} chunks created, target was 1000")
    
    # Get final stats from database
    try:
        final_stats = db_service.get_database_stats()
        milvus_stats = milvus_service.get_collection_stats() if milvus_service.is_available() else {"error": "Milvus not available"}
        logger.info(f"📈 Final DB stats: {final_stats}")
        logger.info(f"📈 Final Milvus stats: {milvus_stats}")
    except Exception as e:
        logger.warning(f"Could not fetch final stats: {e}")
    
    return bootstrapper.total_chunks >= 500  # Lower threshold for success

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 Bootstrap completed successfully!")
        print("💡 You can now test the knowledge base with the frontend or API")
    else:
        print("\n⚠️  Bootstrap completed with issues")
        print("💡 Check the logs above for details")
    
    sys.exit(0 if success else 1)