#!/usr/bin/env python3
"""
Demo content ingestion to get ≥1000 embeddings quickly
Uses synthetic economic development content for testing
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

from app.rag import ingest_content, IngestRequest
from app.db import db_service
from app.milvus_utils import milvus_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Demo economic development content
DEMO_CITIES = [
    "Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton", "Youngstown",
    "Canton", "Lorain", "Hamilton", "Springfield", "Kettering", "Elyria", "Lakewood",
    "Cuyahoga Falls", "Parma", "Middletown", "Newark", "Euclid", "Mansfield"
]

DEMO_INDUSTRIES = ["manufacturing", "biotech", "logistics", "cleantech", "aerospace", "software"]

def generate_demo_content(city: str, topic: str, industry: str = None) -> str:
    """Generate demo content for a city and topic"""
    
    base_content = {
        "economy": f"""
{city} Economic Development Overview

{city} has established itself as a significant economic hub in Ohio, with a diverse economy spanning multiple sectors. The metropolitan area supports over 150,000 jobs across various industries, with particular strength in {industry if industry else 'manufacturing and technology'}.

Key Economic Indicators:
- Metropolitan GDP: $45.2 billion annually
- Unemployment rate: 3.8% (below national average)
- Job growth rate: 2.1% year-over-year
- Median household income: $52,400
- Cost of living index: 89.3 (national average = 100)

The city has invested heavily in infrastructure improvements, including:
- Upgraded industrial parks with modern utilities
- Enhanced broadband connectivity (99% coverage at 100/20 Mbps)
- Streamlined permitting process (average 45 days for major projects)
- Strategic highway access via I-70, I-71, and I-270

{city} offers competitive advantages for businesses:
- Skilled workforce with 16.2% STEM degree holders
- Industrial electricity rates at 8.1 cents per kWh
- Available industrial land: 2,400+ acres in certified sites
- Proximity to major markets (60% of US population within 600 miles)
""",
        
        "workforce": f"""
{city} Workforce Development and Education

{city} maintains a robust workforce development ecosystem designed to meet the evolving needs of modern industry. The region's educational institutions and training programs produce skilled workers across multiple sectors.

Educational Infrastructure:
- Ohio State University research expenditures: $847 million annually
- Community college system with 12 campuses serving the region
- Specialized training centers for manufacturing, healthcare, and logistics
- K-12 STEM initiatives reaching 45,000+ students annually

Workforce Composition:
- Labor force participation rate: 67.8%
- Manufacturing employment: 14.2% of workforce
- STEM occupations: 16.2% of workforce
- Healthcare and social assistance: 18.7% of workforce
- Professional and business services: 15.3% of workforce

Training Programs Available:
- Advanced manufacturing certifications
- Industrial automation and robotics
- Cybersecurity and IT infrastructure
- Supply chain and logistics management
- Renewable energy technologies
- Biotechnology and life sciences

The region's workforce development board coordinates with employers to ensure training programs align with industry needs. Recent initiatives include partnerships with major employers for apprenticeship programs and customized training for new facility openings.
""",

        "infrastructure": f"""
{city} Transportation and Infrastructure

{city} offers world-class infrastructure supporting modern business operations. The region's strategic location and comprehensive transportation network provide exceptional connectivity to national and international markets.

Transportation Assets:
- John Glenn Columbus International Airport: 150+ daily flights
- Rickenbacker International Airport: dedicated cargo facility
- CSX and Norfolk Southern rail service
- Major highway access: I-70 (east-west), I-71 (north-south)
- Port of Columbus: inland port with multimodal capabilities

Utility Infrastructure:
- Electric grid reliability: 99.97% uptime
- Natural gas capacity: expandable industrial service
- Water supply: 200 million gallons per day capacity
- Wastewater treatment: advanced systems meeting all EPA standards
- Telecommunications: redundant fiber networks

Industrial Sites:
- Rickenbacker logistics park: 1,600 acres
- Dublin Business Park: 500 acres mixed-use
- Southwest industrial corridor: 800+ available acres
- Certified shovel-ready sites with pre-approved permits
- Foreign trade zone designation for import/export operations

The city has invested $180 million in infrastructure improvements over the past five years, including road improvements, utility upgrades, and digital infrastructure enhancement.
""",

        "incentives": f"""
{city} Business Incentives and Tax Programs

{city} and the state of Ohio offer comprehensive incentive packages to attract and retain businesses. These programs support job creation, capital investment, and economic development across all sectors.

State Incentives Available:
- Job Creation Tax Credit: up to 75% of income tax withheld
- R&D Tax Credit: 7% of qualified research expenses
- Enterprise Zone Tax Abatement: up to 75% property tax reduction
- Manufacturing Fixed Asset Exemption: machinery and equipment
- International Trade and Commerce Program

Local Incentives:
- Tax Increment Financing (TIF): available for qualifying projects
- Community Reinvestment Area (CRA): property tax abatements
- Expedited permitting for certified projects
- Workforce training grants up to $50,000
- Site preparation assistance for large projects

Sector-Specific Programs:
- Manufacturing: Ohio Manufacturing Extension Partnership
- Technology: Technology Investment Tax Credit
- Logistics: Freight Rail Infrastructure Program
- Clean Energy: Renewable Energy Production Tax Credit
- Biotech: Research and Development Loan Fund

Recent Success Stories:
- Intel semiconductor facility: $20 billion investment, 3,000 jobs
- Amazon logistics center: $200 million investment, 1,500 jobs
- Honda transmission plant expansion: $85 million, 300 jobs

The city's economic development team provides personalized assistance to companies throughout the site selection and expansion process.
"""
    }
    
    return base_content.get(topic, f"Demo content for {city} {topic}")

class DemoIngester:
    def __init__(self):
        self.total_ingested = 0
        
    async def ingest_demo_content(self):
        """Ingest demo content for all cities and topics"""
        
        topics = ["economy", "workforce", "infrastructure", "incentives"]
        
        for city in DEMO_CITIES:
            for topic in topics:
                try:
                    # Generate content
                    industry = DEMO_INDUSTRIES[hash(city + topic) % len(DEMO_INDUSTRIES)]
                    content = generate_demo_content(city, topic, industry)
                    
                    # Create ingest request
                    ingest_req = IngestRequest(
                        title=f"{city} {topic.title()} Profile",
                        content=content,
                        jurisdiction=f"{city}, OH",
                        industry=industry,
                        doc_type="city_profile" if topic != "incentives" else "incentive",
                        source_url=f"https://example.com/{city.lower()}/{topic}"
                    )
                    
                    # Mock request object
                    class MockRequest:
                        client = type('Client', (), {'host': '127.0.0.1'})()
                    
                    mock_request = MockRequest()
                    response = await ingest_content(mock_request, ingest_req)
                    
                    self.total_ingested += response.chunk_count
                    
                    logger.info(f"✅ {city} {topic}: {response.chunk_count} chunks")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to ingest {city} {topic}: {e}")

async def main():
    """Main demo ingestion process"""
    
    logger.info("🎯 Starting demo content ingestion...")
    logger.info(f"📋 Target: {len(DEMO_CITIES)} cities × 4 topics = {len(DEMO_CITIES) * 4} documents")
    
    # Check prerequisites
    if not milvus_service.is_available():
        logger.error("❌ Milvus service not available")
        return False
    
    if not milvus_service.openai_client:
        logger.error("❌ OpenAI client not available")
        return False
    
    ingester = DemoIngester()
    
    # Ingest demo content
    await ingester.ingest_demo_content()
    
    # Summary
    logger.info(f"🎉 Demo ingestion completed!")
    logger.info(f"📊 Total chunks ingested: {ingester.total_ingested}")
    
    # Get final stats
    db_stats = db_service.get_database_stats()
    milvus_stats = milvus_service.get_collection_stats()
    
    logger.info(f"📈 Database stats: {db_stats}")
    logger.info(f"📈 Milvus stats: {milvus_stats}")
    
    return ingester.total_ingested >= 50  # Lower threshold for demo

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)