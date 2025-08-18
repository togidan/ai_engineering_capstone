#!/usr/bin/env python3
"""
End-to-End Knowledge Base Tests
Tests KB upload, search, and agent integration functionality
"""

import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KnowledgeBaseTestSuite:
    def __init__(self):
        self.results = []
        self.test_doc_ids = []
    
    async def test_database_initialization(self) -> Dict[str, Any]:
        """Test that database and Milvus are properly initialized"""
        
        result = {
            "test": "database_initialization",
            "status": "UNKNOWN",
            "notes": "",
            "details": {}
        }
        
        try:
            from app.db import db_service
            from app.milvus_utils import milvus_service
            
            # Test database connection
            db_stats = db_service.get_database_stats()
            
            # Test Milvus connection
            milvus_available = milvus_service.is_available()
            embeddings_available = milvus_service.openai_client is not None
            
            result["details"] = {
                "database_stats": db_stats,
                "milvus_available": milvus_available,
                "embeddings_available": embeddings_available
            }
            
            if milvus_available and embeddings_available:
                result["status"] = "PASS"
                result["notes"] = "All services available"
            else:
                result["status"] = "FAIL"
                missing = []
                if not milvus_available:
                    missing.append("Milvus")
                if not embeddings_available:
                    missing.append("OpenAI embeddings")
                result["notes"] = f"Missing services: {', '.join(missing)}"
                
        except Exception as e:
            result["status"] = "ERROR"
            result["notes"] = f"Initialization test failed: {e}"
        
        return result
    
    async def test_content_ingestion(self) -> Dict[str, Any]:
        """Test creating and ingesting content"""
        
        result = {
            "test": "content_ingestion",
            "status": "UNKNOWN", 
            "notes": "",
            "details": {}
        }
        
        try:
            from app.rag import ingest_content, IngestRequest
            
            # Create test content
            test_content = """
Columbus Economic Development Incentive Package

Tax Increment Financing (TIF)
Columbus offers TIF districts to support economic development projects. Eligible projects include:
- Manufacturing facilities with minimum $2M investment
- Office developments creating 100+ jobs
- Mixed-use developments in targeted areas

Property Tax Abatement
- Up to 75% abatement for 10 years
- Minimum $500K investment required
- Job creation requirements: 1 job per $100K investment

Job Creation Tax Credit
- 75% of state income tax withheld by new employees
- Minimum 25 new full-time positions
- Positions must pay 150% of federal minimum wage
- Credit period: 7 years

Enterprise Zone Benefits
- Machinery and equipment tax exemption
- Inventory tax exemption for manufacturers
- Additional local incentives available
"""
            
            # Create ingest request
            ingest_req = IngestRequest(
                title="Columbus Economic Development Test Document",
                content=test_content,
                jurisdiction="Columbus, OH",
                industry="economic_development",
                doc_type="incentive",
                source_url="https://test.example.com/columbus-incentives"
            )
            
            # Mock request object
            class MockRequest:
                client = type('Client', (), {'host': '127.0.0.1'})()
            
            mock_request = MockRequest()
            response = await ingest_content(mock_request, ingest_req)
            
            # Store for cleanup
            self.test_doc_ids.append(response.doc_id)
            
            result["details"] = {
                "doc_id": response.doc_id,
                "chunk_count": response.chunk_count,
                "auto_metadata": response.auto_metadata
            }
            
            if response.chunk_count >= 3:
                result["status"] = "PASS"
                result["notes"] = f"Successfully ingested {response.chunk_count} chunks"
            else:
                result["status"] = "FAIL"
                result["notes"] = f"Only {response.chunk_count} chunks generated, expected ≥3"
                
        except Exception as e:
            result["status"] = "ERROR"
            result["notes"] = f"Content ingestion failed: {e}"
        
        return result
    
    async def test_knowledge_search(self) -> Dict[str, Any]:
        """Test knowledge base search functionality"""
        
        result = {
            "test": "knowledge_search",
            "status": "UNKNOWN",
            "notes": "",
            "details": {}
        }
        
        try:
            from app.kb import search_knowledge_base, SearchRequest
            
            # Test search
            search_req = SearchRequest(
                query="tax incentives manufacturing Ohio",
                k=5,
                filters={"jurisdiction": "Columbus, OH"}
            )
            
            # Mock request object
            class MockRequest:
                client = type('Client', (), {'host': '127.0.0.1'})()
            
            mock_request = MockRequest()
            search_response = await search_knowledge_base(mock_request, search_req)
            
            result["details"] = {
                "hits_found": len(search_response.hits),
                "out_of_scope": search_response.out_of_scope,
                "top_score": search_response.hits[0].score if search_response.hits else 0
            }
            
            if not search_response.out_of_scope and len(search_response.hits) > 0:
                result["status"] = "PASS"
                result["notes"] = f"Found {len(search_response.hits)} relevant results"
            elif search_response.out_of_scope:
                result["status"] = "FAIL"
                result["notes"] = "Valid economic development query marked as out of scope"
            else:
                result["status"] = "FAIL"
                result["notes"] = "No search results found"
                
        except Exception as e:
            result["status"] = "ERROR"
            result["notes"] = f"Knowledge search failed: {e}"
        
        return result
    
    async def test_agent_integration(self) -> Dict[str, Any]:
        """Test agent-specific endpoints"""
        
        result = {
            "test": "agent_integration",
            "status": "UNKNOWN",
            "notes": "",
            "details": {}
        }
        
        try:
            from app.agent_service import agent_service
            
            # Test knowledge summary
            summary = agent_service.get_knowledge_summary()
            
            # Test document list
            doc_list = agent_service.get_document_list(limit=5)
            
            # Test reading a document if available
            doc_content = None
            if self.test_doc_ids:
                doc_content = agent_service.read_document_by_id(self.test_doc_ids[0])
            
            result["details"] = {
                "knowledge_summary": summary,
                "document_count": len(doc_list),
                "test_doc_readable": doc_content is not None
            }
            
            checks_passed = []
            if summary.get("total_documents", 0) > 0:
                checks_passed.append("Has documents")
            if len(doc_list) > 0:
                checks_passed.append("Document list works")
            if doc_content:
                checks_passed.append("Document reading works")
            
            if len(checks_passed) >= 2:
                result["status"] = "PASS"
                result["notes"] = f"Agent integration working: {', '.join(checks_passed)}"
            else:
                result["status"] = "FAIL"
                result["notes"] = f"Only {len(checks_passed)} agent features working"
                
        except Exception as e:
            result["status"] = "ERROR"
            result["notes"] = f"Agent integration test failed: {e}"
        
        return result
    
    async def test_metadata_extraction(self) -> Dict[str, Any]:
        """Test auto-metadata extraction"""
        
        result = {
            "test": "metadata_extraction", 
            "status": "UNKNOWN",
            "notes": "",
            "details": {}
        }
        
        try:
            from app.text_utils import text_processor
            
            # Test content
            test_text = """
Cleveland Manufacturing Incentive Program
State of Ohio Enterprise Zone Benefits

Cleveland, Ohio offers comprehensive incentives for advanced manufacturing companies looking to establish operations in the region. The city's enterprise zone provides significant property tax abatements for qualifying manufacturing projects.

Key benefits include:
- Property tax abatement up to 75% for 15 years
- Machinery and equipment tax exemption
- Job creation requirements: minimum 50 new positions
- Investment threshold: $5 million minimum
- Workforce development partnerships with Cleveland State University

For biotech and aerospace companies, additional R&D tax credits are available through the state's technology investment program.
"""
            
            metadata = text_processor.extract_metadata(test_text, "cleveland_manufacturing.pdf")
            
            result["details"] = metadata
            
            # Check metadata quality
            quality_checks = []
            if metadata.get("jurisdiction") and "cleveland" in metadata["jurisdiction"].lower():
                quality_checks.append("Jurisdiction extracted")
            if metadata.get("industry") and metadata["industry"] in ["manufacturing", "advanced manufacturing"]:
                quality_checks.append("Industry extracted")
            if metadata.get("doc_type") in ["incentive", "policy", "economic_data"]:
                quality_checks.append("Doc type classified")
            if metadata.get("keywords") and len(metadata["keywords"]) > 10:
                quality_checks.append("Keywords extracted")
            if metadata.get("summary") and len(metadata["summary"]) > 50:
                quality_checks.append("Summary generated")
            
            if len(quality_checks) >= 3:
                result["status"] = "PASS"
                result["notes"] = f"Metadata extraction working: {', '.join(quality_checks)}"
            else:
                result["status"] = "FAIL"
                result["notes"] = f"Only {len(quality_checks)} metadata features working"
                
        except Exception as e:
            result["status"] = "ERROR"
            result["notes"] = f"Metadata extraction test failed: {e}"
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all knowledge base tests"""
        
        logger.info("🧪 Starting Knowledge Base Integration Tests")
        
        tests = [
            ("Database Initialization", self.test_database_initialization),
            ("Content Ingestion", self.test_content_ingestion),
            ("Knowledge Search", self.test_knowledge_search),
            ("Agent Integration", self.test_agent_integration),
            ("Metadata Extraction", self.test_metadata_extraction)
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            logger.info(f"🔍 Running: {test_name}")
            
            start_time = time.time()
            result = await test_func()
            end_time = time.time()
            
            result["latency_ms"] = round((end_time - start_time) * 1000, 2)
            self.results.append(result)
            
            # Log result
            status_emoji = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            logger.info(f"   {status_emoji} {result['status']}: {result['notes']}")
            logger.info(f"   Latency: {result['latency_ms']}ms")
            
            if result["status"] == "PASS":
                passed += 1
            else:
                failed += 1
            
            # Brief delay between tests
            await asyncio.sleep(0.5)
        
        # Generate summary
        total_tests = len(self.results)
        pass_rate = (passed / total_tests) * 100 if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 1),
            "results": self.results,
            "overall_status": "PASS" if passed == total_tests else "FAIL"
        }
        
        # Log final summary
        logger.info(f"🎯 Knowledge Base Test Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {passed}")
        logger.info(f"   Failed: {failed}")
        logger.info(f"   Pass Rate: {pass_rate:.1f}%")
        logger.info(f"   Overall: {'✅ PASS' if summary['overall_status'] == 'PASS' else '❌ FAIL'}")
        
        return summary
    
    def log_detailed_results(self):
        """Log detailed test results"""
        
        logger.info("\n" + "="*100)
        logger.info("DETAILED KNOWLEDGE BASE TEST RESULTS")
        logger.info("="*100)
        
        for result in self.results:
            logger.info(f"\nTest: {result['test']}")
            logger.info(f"Status: {result['status']}")
            logger.info(f"Notes: {result['notes']}")
            logger.info(f"Latency: {result['latency_ms']}ms")
            if result.get('details'):
                logger.info(f"Details: {result['details']}")
        
        logger.info("="*100)

async def main():
    """Main test execution"""
    
    test_suite = KnowledgeBaseTestSuite()
    
    try:
        summary = await test_suite.run_all_tests()
        
        # Log detailed results
        test_suite.log_detailed_results()
        
        # Return success if all tests passed
        return summary["overall_status"] == "PASS"
        
    except Exception as e:
        logger.error(f"❌ Knowledge Base test suite execution failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)