#!/usr/bin/env python3
"""
Bootstrap Knowledge Base with Wikipedia data for US cities
Target: ≥1000 embeddings from ~50 major US cities
"""

import os
import sys
import logging
import time
import asyncio
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

from app.rag import ingest_content, IngestRequest
from app.db import db_service
from app.milvus_utils import milvus_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Major US cities for economic development analysis
MAJOR_US_CITIES = [
    "New York City", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
    "Fort Worth", "Columbus, Ohio", "Charlotte, North Carolina", "San Francisco", 
    "Indianapolis", "Seattle", "Denver", "Washington, D.C.", "Boston", "El Paso",
    "Nashville", "Detroit", "Oklahoma City", "Portland, Oregon", "Las Vegas", 
    "Memphis, Tennessee", "Louisville, Kentucky", "Baltimore", "Milwaukee", 
    "Albuquerque", "Tucson", "Fresno, California", "Sacramento", "Kansas City, Missouri",
    "Mesa, Arizona", "Atlanta", "Colorado Springs", "Virginia Beach", "Raleigh, North Carolina",
    "Omaha", "Miami", "Oakland, California", "Minneapolis", "Tulsa", "Wichita", "New Orleans"
]

# Relevant sections for economic development
RELEVANT_SECTIONS = [
    "Economy", "Transportation", "Infrastructure", "Demographics", "Industry", 
    "Logistics", "Business", "Manufacturing", "Technology", "Education", 
    "Research", "Universities", "Development"
]

class WikipediaIngester:
    def __init__(self):
        self.total_ingested = 0
        self.failed_cities = []
        wikipedia.set_rate_limiting(True)  # Be respectful to Wikipedia
        
    def extract_relevant_content(self, page_content: str, city_name: str) -> list:
        """Extract relevant sections for economic development"""
        
        sections = []
        lines = page_content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Check if line is a section header
            if line.startswith('=') and any(keyword.lower() in line.lower() for keyword in RELEVANT_SECTIONS):
                # Save previous section if it exists and has content
                if current_section and current_content:
                    content = '\n'.join(current_content).strip()
                    if len(content) > 500:  # Only include substantial sections
                        sections.append({
                            "title": f"{city_name} - {current_section}",
                            "content": content,
                            "section": current_section
                        })
                
                # Start new section
                current_section = line.strip('= ')
                current_content = []
            
            elif current_section and line.strip():
                current_content.append(line)
        
        # Add final section
        if current_section and current_content:
            content = '\n'.join(current_content).strip()
            if len(content) > 500:
                sections.append({
                    "title": f"{city_name} - {current_section}",
                    "content": content,
                    "section": current_section
                })
        
        return sections
    
    async def ingest_city(self, city_name: str):
        """Ingest Wikipedia data for a single city"""
        
        try:
            logger.info(f"🏙️  Processing {city_name}...")
            
            # Search for the city page
            search_results = wikipedia.search(city_name, results=5)
            if not search_results:
                logger.warning(f"❌ No Wikipedia results for {city_name}")
                self.failed_cities.append(city_name)
                return
            
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
                    self.failed_cities.append(city_name)
                    return
            except wikipedia.exceptions.PageError:
                logger.warning(f"❌ Page not found for {city_name}")
                self.failed_cities.append(city_name)
                return
            
            # Extract relevant sections
            sections = self.extract_relevant_content(page.content, city_name)
            
            if not sections:
                logger.warning(f"⚠️  No relevant sections found for {city_name}")
                # Still try to ingest the full content if it's substantial
                if len(page.content) > 2000:
                    sections = [{
                        "title": f"{city_name} - Overview",
                        "content": page.content[:5000],  # First 5000 chars
                        "section": "Overview"
                    }]
                else:
                    self.failed_cities.append(city_name)
                    return
            
            # Ingest each section
            city_chunks = 0
            for section in sections:
                try:
                    # Determine jurisdiction and industry
                    jurisdiction = self._extract_jurisdiction(city_name)
                    industry = self._guess_industry(section["content"])
                    doc_type = self._guess_doc_type(section["section"])
                    
                    # Create ingest request
                    ingest_req = IngestRequest(
                        title=section["title"],
                        content=section["content"],
                        jurisdiction=jurisdiction,
                        industry=industry,
                        doc_type=doc_type,
                        source_url=page.url
                    )
                    
                    # Mock request object for the API call
                    class MockRequest:
                        pass
                    
                    mock_request = MockRequest()
                    response = await ingest_content(mock_request, ingest_req)
                    
                    city_chunks += response.chunk_count
                    self.total_ingested += response.chunk_count
                    
                    logger.info(f"   ✅ {section['title']}: {response.chunk_count} chunks")
                    
                    # Rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"   ❌ Failed to ingest section {section['title']}: {e}")
            
            logger.info(f"✅ {city_name} completed: {city_chunks} total chunks")
            
        except Exception as e:
            logger.error(f"❌ Failed to process {city_name}: {e}")
            self.failed_cities.append(city_name)
    
    def _extract_jurisdiction(self, city_name: str) -> str:
        """Extract jurisdiction from city name"""
        if "," in city_name:
            return city_name  # Already has state
        else:
            # For major cities, we can add common state mappings
            state_mapping = {
                "New York City": "New York, NY",
                "Los Angeles": "Los Angeles, CA",
                "Chicago": "Chicago, IL",
                "Houston": "Houston, TX",
                # Add more as needed
            }
            return state_mapping.get(city_name, city_name)
    
    def _guess_industry(self, content: str) -> str:
        """Guess primary industry from content"""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ["manufacturing", "factory", "industrial"]):
            return "manufacturing"
        elif any(term in content_lower for term in ["tech", "software", "silicon"]):
            return "technology"
        elif any(term in content_lower for term in ["biotech", "pharmaceutical", "medical"]):
            return "biotech"
        elif any(term in content_lower for term in ["logistics", "shipping", "port", "freight"]):
            return "logistics"
        elif any(term in content_lower for term in ["aerospace", "aviation", "aircraft"]):
            return "aerospace"
        else:
            return None
    
    def _guess_doc_type(self, section_name: str) -> str:
        """Guess document type from section name"""
        section_lower = section_name.lower()
        
        if "economy" in section_lower:
            return "economic_data"
        elif any(term in section_lower for term in ["transport", "infrastructure"]):
            return "city_profile"
        else:
            return "city_profile"

async def main():
    """Main ingestion process"""
    
    logger.info("🌐 Starting Wikipedia ingestion for US cities...")
    logger.info(f"📋 Target: {len(MAJOR_US_CITIES)} cities, aiming for ≥1000 embeddings")
    
    # Check prerequisites
    if not milvus_service.is_available():
        logger.error("❌ Milvus service not available")
        return False
    
    if not milvus_service.openai_client:
        logger.error("❌ OpenAI client not available")
        return False
    
    ingester = WikipediaIngester()
    
    # Process each city
    start_time = time.time()
    for i, city in enumerate(MAJOR_US_CITIES, 1):
        logger.info(f"📍 [{i}/{len(MAJOR_US_CITIES)}] Processing {city}...")
        await ingester.ingest_city(city)
        
        # Progress update every 10 cities
        if i % 10 == 0:
            elapsed = time.time() - start_time
            logger.info(f"⏱️  Progress: {i}/{len(MAJOR_US_CITIES)} cities, {ingester.total_ingested} chunks, {elapsed:.1f}s elapsed")
    
    # Final summary
    elapsed = time.time() - start_time
    logger.info(f"🎉 Wikipedia ingestion completed!")
    logger.info(f"📊 Summary:")
    logger.info(f"   - Total chunks ingested: {ingester.total_ingested}")
    logger.info(f"   - Cities processed: {len(MAJOR_US_CITIES) - len(ingester.failed_cities)}")
    logger.info(f"   - Failed cities: {len(ingester.failed_cities)}")
    logger.info(f"   - Total time: {elapsed:.1f} seconds")
    
    if ingester.failed_cities:
        logger.warning(f"⚠️  Failed cities: {', '.join(ingester.failed_cities)}")
    
    # Check if we met the target
    if ingester.total_ingested >= 1000:
        logger.info("✅ Target of ≥1000 embeddings achieved!")
    else:
        logger.warning(f"⚠️  Only {ingester.total_ingested} embeddings created, target was 1000")
    
    # Get final stats
    db_stats = db_service.get_database_stats()
    milvus_stats = milvus_service.get_collection_stats()
    
    logger.info(f"📈 Final database stats: {db_stats}")
    logger.info(f"📈 Final Milvus stats: {milvus_stats}")
    
    return ingester.total_ingested >= 1000

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)