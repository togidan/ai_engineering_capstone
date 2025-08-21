#!/usr/bin/env python3
"""
Simple demo content ingestion to bootstrap the knowledge base
Creates synthetic economic development content for testing
Target: Generate enough content to reach ≥1000 embeddings
"""

import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_demo_documents():
    """Create demo documents directly in the knowledge base"""
    
    try:
        from app.db import db_service
        from app.milvus_utils import milvus_service
        from app.text_utils import text_processor
        
        # Check prerequisites
        if not milvus_service.is_available():
            logger.error("❌ Milvus service not available")
            return False
        
        if not milvus_service.openai_client:
            logger.error("❌ OpenAI client not available for embeddings")
            return False
        
        logger.info("🚀 Starting demo content creation...")
        
        # Demo cities in Ohio
        cities = [
            "Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton",
            "Youngstown", "Canton", "Springfield", "Hamilton", "Kettering",
            "Lorain", "Elyria", "Lakewood", "Parma", "Middletown", "Newark",
            "Euclid", "Mansfield", "Lima", "Zanesville", "Marietta"
        ]
        
        # Document types and content templates
        content_templates = {
            "economic_profile": {
                "doc_type": "city_profile",
                "template": """
{city} Economic Development Profile

Metropolitan Overview:
{city} serves as a key economic center in Ohio with a diverse industrial base and growing technology sector. The metropolitan area encompasses a population of approximately {population:,} residents across {counties} counties, providing businesses access to a skilled workforce and comprehensive infrastructure.

Economic Indicators:
• Gross Metropolitan Product: ${gmp:.1f} billion annually
• Employment Rate: {employment:.1f}% (above state average)
• Median Household Income: ${income:,}
• Cost of Living Index: {col_index} (US average = 100)
• Industrial Vacancy Rate: {vacancy:.1f}%

Key Industry Clusters:
• {industry1}: {industry1_pct:.1f}% of employment ({industry1_jobs:,} jobs)
• {industry2}: {industry2_pct:.1f}% of employment ({industry2_jobs:,} jobs) 
• {industry3}: {industry3_pct:.1f}% of employment ({industry3_jobs:,} jobs)
• Professional Services: {prof_services:.1f}% of employment

Infrastructure Assets:
• Electric Power: {power_reliability:.1f}% grid reliability, competitive industrial rates
• Transportation: Access to {highway_count} major highways, {rail_lines} rail services
• Telecommunications: {broadband_coverage:.1f}% fiber coverage, redundant data networks
• Water/Sewer: {water_capacity} MGD capacity with expansion capability

Workforce Development:
• Labor Force Participation: {labor_participation:.1f}%
• STEM Employment: {stem_pct:.1f}% of workforce
• Higher Education: {universities} universities, {community_colleges} community colleges
• Training Programs: {training_programs} workforce development initiatives
"""
            },
            
            "incentive_guide": {
                "doc_type": "incentive",
                "template": """
{city} Business Incentive Guide

Tax Incentive Programs:

Job Creation Tax Credit
• Credit Amount: Up to {job_credit_pct}% of state income tax withheld by new employees
• Minimum Job Requirement: {min_jobs} new full-time positions
• Wage Threshold: {wage_threshold:.1f}% of county average wage
• Agreement Term: {agreement_term} years
• Eligible Industries: Manufacturing, technology, logistics, research & development

Enterprise Zone Tax Abatement
• Property Tax Exemption: Up to {property_exemption}% for {exemption_years} years
• Eligible Property: Real estate, machinery, equipment, inventory
• Investment Threshold: ${min_investment:,} minimum
• Job Creation Requirement: {jobs_per_investment} jobs per $1M investment

Research & Development Tax Credit
• Credit Rate: {rd_credit}% of qualified research expenses
• Maximum Annual Credit: ${max_rd_credit:,}
• Carry-forward Period: {carryforward} years
• Eligible Activities: New product development, process improvement, software development

Local Incentives:

Tax Increment Financing (TIF)
• Available for: Infrastructure improvements, site preparation, environmental remediation
• Financing Period: Up to {tif_years} years
• Project Threshold: ${tif_threshold:,} minimum investment
• Public Benefit: {tif_benefit_pct}% of project value in public benefits

Fee Waivers and Reductions
• Building Permit Fees: Up to {permit_waiver}% reduction for qualifying projects
• Impact Fees: {impact_fee_policy}
• Expedited Review: {expedited_timeline} day review for certified projects

Utility Rate Incentives:
• Industrial Power: Competitive rates starting at {power_rate}¢/kWh
• Natural Gas: Economic development rates available
• Water/Sewer: Volume discounts for large users
"""
            },
            
            "workforce_data": {
                "doc_type": "economic_data", 
                "template": """
{city} Workforce Analysis

Labor Market Statistics:

Total Labor Force: {labor_force:,}
• Employed: {employed:,} ({employment_rate:.1f}%)
• Unemployed: {unemployed:,} ({unemployment_rate:.1f}%)
• Not in Labor Force: {not_in_lf:,}

Educational Attainment (Age 25+):
• Less than High School: {less_hs:.1f}%
• High School Graduate: {hs_grad:.1f}%
• Some College: {some_college:.1f}%
• Bachelor's Degree: {bachelors:.1f}%
• Graduate/Professional: {graduate:.1f}%

Occupational Distribution:
• Management/Professional: {mgmt_prof:.1f}% ({mgmt_prof_jobs:,} jobs)
• Sales and Office: {sales_office:.1f}% ({sales_office_jobs:,} jobs)
• Production/Transportation: {production:.1f}% ({production_jobs:,} jobs)
• Service Occupations: {service:.1f}% ({service_jobs:,} jobs)

STEM Workforce:
• Total STEM Employment: {stem_total:,} ({stem_pct:.1f}% of workforce)
• Computer/Mathematical: {comp_math:,} jobs
• Engineering: {engineering:,} jobs
• Life Sciences: {life_sciences:,} jobs
• Physical Sciences: {physical_sciences:,} jobs

Manufacturing Workforce:
• Total Manufacturing Employment: {mfg_total:,}
• Average Wage: ${mfg_wage:,} annually
• Major Subsectors: {mfg_subsector1}, {mfg_subsector2}, {mfg_subsector3}
• Skills in Demand: {skill1}, {skill2}, {skill3}

Training and Development Resources:
• {training_provider1}: {training_desc1}
• {training_provider2}: {training_desc2}
• {training_provider3}: {training_desc3}
• Apprenticeship Programs: {apprenticeship_programs} active programs
• Annual Training Capacity: {training_capacity:,} participants
"""
            }
        }
        
        total_chunks = 0
        documents_created = 0
        
        for i, city in enumerate(cities):
            for content_type, template_info in content_templates.items():
                try:
                    # Generate realistic but synthetic data
                    base_pop = 100000 + (i * 50000)
                    
                    # Fill in template variables with synthetic data
                    content = template_info["template"].format(
                        city=city,
                        population=base_pop + (hash(city) % 500000),
                        counties=2 + (hash(city) % 3),
                        gmp=round(5.2 + (hash(city) % 50), 1),
                        employment=round(94.5 + (hash(city) % 30) / 10, 1),
                        income=45000 + (hash(city) % 25000),
                        col_index=85 + (hash(city) % 20),
                        vacancy=round(3.5 + (hash(city) % 40) / 10, 1),
                        industry1="Manufacturing",
                        industry1_pct=round(12.5 + (hash(city) % 50) / 10, 1),
                        industry1_jobs=int((base_pop * 0.125) + (hash(city) % 10000)),
                        industry2="Healthcare",
                        industry2_pct=round(15.2 + (hash(city) % 30) / 10, 1),
                        industry2_jobs=int((base_pop * 0.152) + (hash(city) % 8000)),
                        industry3="Professional Services",
                        industry3_pct=round(11.8 + (hash(city) % 40) / 10, 1),
                        industry3_jobs=int((base_pop * 0.118) + (hash(city) % 6000)),
                        prof_services=round(18.5 + (hash(city) % 25) / 10, 1),
                        power_reliability=round(99.1 + (hash(city) % 8) / 10, 1),
                        highway_count=2 + (hash(city) % 4),
                        rail_lines="2 Class I railroads",
                        broadband_coverage=round(85.5 + (hash(city) % 120) / 10, 1),
                        water_capacity=f"{50 + (hash(city) % 150)}",
                        labor_participation=round(67.2 + (hash(city) % 80) / 10, 1),
                        stem_pct=round(14.5 + (hash(city) % 60) / 10, 1),
                        universities=1 + (hash(city) % 3),
                        community_colleges=1 + (hash(city) % 2),
                        training_programs=8 + (hash(city) % 15),
                        # Incentive template variables
                        job_credit_pct=60 + (hash(city) % 15),
                        min_jobs=10 + (hash(city) % 15),
                        wage_threshold=round(75 + (hash(city) % 50), 1),
                        agreement_term=5 + (hash(city) % 5),
                        property_exemption=50 + (hash(city) % 25),
                        exemption_years=10 + (hash(city) % 5),
                        min_investment=500000 + (hash(city) % 500000),
                        jobs_per_investment=5 + (hash(city) % 10),
                        rd_credit=5 + (hash(city) % 5),
                        max_rd_credit=100000 + (hash(city) % 400000),
                        carryforward=5 + (hash(city) % 5),
                        tif_years=15 + (hash(city) % 10),
                        tif_threshold=1000000 + (hash(city) % 2000000),
                        tif_benefit_pct=75 + (hash(city) % 20),
                        permit_waiver=50 + (hash(city) % 30),
                        impact_fee_policy="Reduced by 50% for manufacturing projects",
                        expedited_timeline=30 + (hash(city) % 30),
                        power_rate=round(6.5 + (hash(city) % 25) / 10, 1),
                        # Workforce template variables
                        labor_force=int(base_pop * 0.65),
                        employed=int(base_pop * 0.62),
                        unemployed=int(base_pop * 0.03),
                        not_in_lf=int(base_pop * 0.35),
                        employment_rate=round(95.2 + (hash(city) % 30) / 10, 1),
                        unemployment_rate=round(4.8 - (hash(city) % 30) / 10, 1),
                        less_hs=round(8.5 + (hash(city) % 50) / 10, 1),
                        hs_grad=round(28.5 + (hash(city) % 60) / 10, 1),
                        some_college=round(32.2 + (hash(city) % 40) / 10, 1),
                        bachelors=round(20.8 + (hash(city) % 80) / 10, 1),
                        graduate=round(10.0 + (hash(city) % 60) / 10, 1),
                        mgmt_prof=round(35.2 + (hash(city) % 50) / 10, 1),
                        mgmt_prof_jobs=int(base_pop * 0.352 * 0.65),
                        sales_office=round(23.8 + (hash(city) % 40) / 10, 1),
                        sales_office_jobs=int(base_pop * 0.238 * 0.65),
                        production=round(18.5 + (hash(city) % 60) / 10, 1),
                        production_jobs=int(base_pop * 0.185 * 0.65),
                        service=round(22.5 + (hash(city) % 30) / 10, 1),
                        service_jobs=int(base_pop * 0.225 * 0.65),
                        stem_total=int(base_pop * 0.145 * 0.65),
                        comp_math=int(base_pop * 0.055 * 0.65),
                        engineering=int(base_pop * 0.045 * 0.65),
                        life_sciences=int(base_pop * 0.025 * 0.65),
                        physical_sciences=int(base_pop * 0.020 * 0.65),
                        mfg_total=int(base_pop * 0.125 * 0.65),
                        mfg_wage=52000 + (hash(city) % 18000),
                        mfg_subsector1="Automotive Components",
                        mfg_subsector2="Food Processing", 
                        mfg_subsector3="Machinery Manufacturing",
                        skill1="CNC Operation",
                        skill2="Quality Control",
                        skill3="Industrial Maintenance",
                        training_provider1=f"{city} Community College",
                        training_desc1="Manufacturing technology, healthcare, IT programs",
                        training_provider2="Ohio Manufacturing Extension Partnership",
                        training_desc2="Lean manufacturing, quality systems, safety training",
                        training_provider3=f"{city} Workforce Development",
                        training_desc3="Job placement, skills assessment, apprenticeships",
                        apprenticeship_programs=3 + (hash(city) % 8),
                        training_capacity=500 + (hash(city) % 1500),
                    )
                    
                    # Extract metadata
                    auto_metadata = text_processor.extract_metadata(content, f"{city}_{content_type}")
                    
                    # Insert document into database
                    doc_id = db_service.insert_document(
                        path=f"/virtual/{city.lower()}_{content_type}",
                        name=f"{city} {content_type.replace('_', ' ').title()}",
                        file_size=len(content.encode('utf-8')),
                        description=auto_metadata["summary"]
                    )
                    
                    if doc_id:
                        # Generate chunks
                        chunks = text_processor.chunk_text(content)
                        
                        if chunks:
                            # Insert chunks
                            chunk_ids = db_service.insert_chunks(doc_id, chunks)
                            
                            if chunk_ids:
                                # Prepare data for Milvus insertion
                                chunks_data = []
                                for chunk_id, chunk_text in zip(chunk_ids, chunks):
                                    chunks_data.append({
                                        "milvus_pk": chunk_id,
                                        "text": chunk_text,
                                        "jurisdiction": f"{city}, OH",
                                        "industry": "economic_development",
                                        "doc_type": template_info["doc_type"]
                                    })
                                
                                # Insert into Milvus
                                if milvus_service.insert_chunks(chunks_data):
                                    # Update chunk records with milvus_pk
                                    for chunk_id in chunk_ids:
                                        db_service.update_chunk_milvus_pk(chunk_id, chunk_id)
                                    
                                    total_chunks += len(chunks)
                                    documents_created += 1
                                    
                                    logger.info(f"✅ {city} {content_type}: {len(chunks)} chunks")
                                else:
                                    logger.warning(f"⚠️ Milvus insertion failed for {city} {content_type}")
                            else:
                                logger.error(f"❌ Failed to insert chunks for {city} {content_type}")
                        else:
                            logger.warning(f"⚠️ No chunks generated for {city} {content_type}")
                    else:
                        logger.error(f"❌ Failed to insert document for {city} {content_type}")
                
                except Exception as e:
                    logger.error(f"❌ Failed to create {city} {content_type}: {e}")
        
        # Final summary
        logger.info(f"🎉 Demo content creation completed!")
        logger.info(f"📊 Summary:")
        logger.info(f"   - Documents created: {documents_created}")
        logger.info(f"   - Total chunks: {total_chunks}")
        logger.info(f"   - Target met: {'✅ Yes' if total_chunks >= 1000 else '❌ No'} (target: ≥1000)")
        
        # Get final stats
        db_stats = db_service.get_database_stats()
        milvus_stats = milvus_service.get_collection_stats()
        
        logger.info(f"📈 Final database stats: {db_stats}")
        logger.info(f"📈 Final Milvus stats: {milvus_stats}")
        
        return total_chunks >= 1000
        
    except Exception as e:
        logger.error(f"💥 Demo content creation failed: {e}")
        return False

def main():
    """Main function"""
    
    logger.info("🎯 Starting simple demo content ingestion...")
    
    success = create_demo_documents()
    
    if success:
        logger.info("✅ Demo content ingestion completed successfully!")
        logger.info("💡 Next steps:")
        logger.info("   - Start the API server: uvicorn app.main:app --reload")
        logger.info("   - Test the Knowledge Base endpoints")
        logger.info("   - Try RAG search queries")
    else:
        logger.error("❌ Demo content ingestion failed!")
        logger.error("🔧 Check your environment variables and service availability")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)