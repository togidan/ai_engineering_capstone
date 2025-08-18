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
    "Denver, Colorado", "Colorado Springs, Colorado", 
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

# API endpoint
API_BASE = "http://localhost:8000"

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
        """Upload content to knowledge base via API"""
        try:
            # Create a text file in memory
            file_content = f"# {city_name} Economic Development Profile\n\n"
            file_content += f"Source: Wikipedia - {source_url}\n\n"
            file_content += content
            
            # Prepare file upload
            files = {
                'file': (f"{city_name.replace(', ', '_')}_econ_profile.txt", 
                        file_content.encode('utf-8'), 
                        'text/plain')
            }
            
            # Upload to KB
            response = requests.post(f"{API_BASE}/kb/upload", files=files, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                self.total_documents += 1
                self.total_chunks += result.get('chunk_count', 0)
                logger.info(f"   ✅ Uploaded: {result.get('chunk_count', 0)} chunks")
                return True
            else:
                logger.error(f"   ❌ Upload failed: {response.status_code} - {response.text}")
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
    
    # Test API connectivity
    try:
        response = requests.get(f"{API_BASE}/kb/stats", timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ Cannot connect to API at {API_BASE}")
            return False
        logger.info("✅ API connectivity confirmed")
    except Exception as e:
        logger.error(f"❌ API connection failed: {e}")
        logger.info("💡 Make sure the backend server is running: uvicorn app.main:app --reload")
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
    
    # Get final stats from API
    try:
        response = requests.get(f"{API_BASE}/kb/stats")
        if response.status_code == 200:
            stats = response.json()
            logger.info(f"📈 Final KB stats: {stats}")
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