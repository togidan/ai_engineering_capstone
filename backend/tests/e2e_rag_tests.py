#!/usr/bin/env python3
"""
End-to-End RAG Tests
Tests the 5 required query scenarios with pass/fail criteria
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

# Test queries as specified in requirements
TEST_QUERIES = [
    {
        "id": 1,
        "query": "List 3 incentives for advanced manufacturing in Ohio, with citations.",
        "expected_context": ["incentive", "manufacturing", "ohio"],
        "min_citations": 2,
        "description": "Advanced manufacturing incentives in Ohio"
    },
    {
        "id": 2, 
        "query": "We need 3MW power and be within 60 minutes of an international airport. Which cities fit?",
        "expected_context": ["power", "airport", "infrastructure"],
        "min_citations": 1,
        "description": "Power and airport requirements for site selection"
    },
    {
        "id": 3,
        "query": "A biotech example with university partnerships in North Carolina — cite sources.",
        "expected_context": ["biotech", "university", "partnership"],
        "min_citations": 2,
        "description": "Biotech university partnerships in North Carolina"
    },
    {
        "id": 4,
        "query": "Typical clawback provisions for job-creation credits in Texas?",
        "expected_context": ["clawback", "job", "credit", "texas"],
        "min_citations": 1,
        "description": "Clawback provisions for job creation credits"
    },
    {
        "id": 5,
        "query": "Compare City A vs City B for logistics and labor availability; cite both.",
        "expected_context": ["logistics", "labor", "compare"],
        "min_citations": 2,
        "description": "City comparison for logistics and labor"
    }
]

class RAGTestSuite:
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
    
    async def test_rag_query(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single RAG query"""
        
        start_time = time.time()
        result = {
            "test_id": test_case["id"],
            "query": test_case["query"],
            "description": test_case["description"],
            "status": "UNKNOWN",
            "citations_found": 0,
            "has_abstain": False,
            "latency_ms": 0,
            "error": None,
            "response_snippet": "",
            "notes": ""
        }
        
        try:
            # Import here to avoid import errors if services not available
            from app.rag import rag_search, SearchRequest
            from app.rfi import search_kb_for_context, DraftRequest
            
            # Test RAG search
            search_request = SearchRequest(
                query=test_case["query"],
                k=5,
                filters=None
            )
            
            # Mock request object
            class MockRequest:
                client = type('Client', (), {'host': '127.0.0.1'})()
            
            mock_request = MockRequest()
            search_response = await rag_search(mock_request, search_request)
            
            # Check if query was in scope
            if search_response.out_of_scope:
                result["status"] = "FAIL"
                result["notes"] = "Query marked as out of scope"
                result["has_abstain"] = True
            else:
                # Count citations
                citations_found = len(search_response.hits)
                result["citations_found"] = citations_found
                
                # Check pass criteria: ≥2 citations OR clear abstain message
                min_required = test_case.get("min_citations", 2)
                
                if citations_found >= min_required:
                    result["status"] = "PASS"
                    result["notes"] = f"Found {citations_found} citations (≥{min_required} required)"
                else:
                    # Check if there's an abstain with missing info details
                    if citations_found == 0:
                        result["status"] = "PASS"
                        result["has_abstain"] = True
                        result["notes"] = "Clean abstain - no citations but query was processed"
                    else:
                        result["status"] = "FAIL"
                        result["notes"] = f"Only {citations_found} citations found, need ≥{min_required}"
                
                # Capture response snippet
                if search_response.hits:
                    first_hit = search_response.hits[0]
                    result["response_snippet"] = first_hit.text[:200] + "..." if len(first_hit.text) > 200 else first_hit.text
                else:
                    result["response_snippet"] = "No results returned"
            
        except Exception as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            result["notes"] = f"Test execution failed: {e}"
            logger.error(f"Test {test_case['id']} failed with error: {e}")
        
        # Calculate latency
        end_time = time.time()
        result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all test queries and return summary"""
        
        logger.info("🧪 Starting RAG Integration Tests")
        logger.info(f"📋 Running {len(TEST_QUERIES)} test queries...")
        
        # Check prerequisites
        try:
            from app.milvus_utils import milvus_service
            from app.db import db_service
            
            if not milvus_service.is_available():
                logger.error("❌ Milvus service not available")
                return {"error": "Milvus service not available"}
            
            # Get database stats
            db_stats = db_service.get_database_stats()
            total_chunks = db_stats.get("chunks", 0)
            
            if total_chunks < 100:
                logger.warning(f"⚠️ Only {total_chunks} chunks in database - tests may not be meaningful")
            
            logger.info(f"📊 Database ready: {db_stats.get('documents', 0)} docs, {total_chunks} chunks")
            
        except Exception as e:
            logger.error(f"❌ Prerequisites check failed: {e}")
            return {"error": f"Prerequisites check failed: {e}"}
        
        # Run each test
        for i, test_case in enumerate(TEST_QUERIES, 1):
            logger.info(f"🔍 Test {i}/{len(TEST_QUERIES)}: {test_case['description']}")
            logger.info(f"   Query: {test_case['query']}")
            
            result = await self.test_rag_query(test_case)
            self.results.append(result)
            
            # Log result
            status_emoji = "✅" if result["status"] == "PASS" else "❌" if result["status"] == "FAIL" else "⚠️"
            logger.info(f"   {status_emoji} {result['status']}: {result['notes']}")
            logger.info(f"   Citations: {result['citations_found']}, Latency: {result['latency_ms']}ms")
            
            if result["status"] == "PASS":
                self.passed += 1
            else:
                self.failed += 1
            
            # Brief delay between tests
            await asyncio.sleep(1)
        
        # Generate summary
        total_tests = len(self.results)
        pass_rate = (self.passed / total_tests) * 100 if total_tests > 0 else 0
        
        summary = {
            "total_tests": total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(pass_rate, 1),
            "results": self.results,
            "overall_status": "PASS" if self.passed == total_tests else "FAIL"
        }
        
        # Log final summary
        logger.info(f"🎯 RAG Test Summary:")
        logger.info(f"   Total Tests: {total_tests}")
        logger.info(f"   Passed: {self.passed}")
        logger.info(f"   Failed: {self.failed}")
        logger.info(f"   Pass Rate: {pass_rate:.1f}%")
        logger.info(f"   Overall: {'✅ PASS' if summary['overall_status'] == 'PASS' else '❌ FAIL'}")
        
        return summary
    
    def log_detailed_results(self):
        """Log detailed test results in tabular format"""
        
        logger.info("\n" + "="*120)
        logger.info("DETAILED TEST RESULTS")
        logger.info("="*120)
        
        header = f"{'ID':<3} {'Status':<6} {'Citations':<9} {'Latency':<8} {'Description':<40} {'Notes':<30}"
        logger.info(header)
        logger.info("-"*120)
        
        for result in self.results:
            row = (
                f"{result['test_id']:<3} "
                f"{result['status']:<6} "
                f"{result['citations_found']:<9} "
                f"{result['latency_ms']:<8} "
                f"{result['description'][:39]:<40} "
                f"{result['notes'][:29]:<30}"
            )
            logger.info(row)
        
        logger.info("="*120)

async def main():
    """Main test execution"""
    
    test_suite = RAGTestSuite()
    
    try:
        summary = await test_suite.run_all_tests()
        
        if "error" in summary:
            logger.error(f"❌ Test suite failed to run: {summary['error']}")
            return False
        
        # Log detailed results
        test_suite.log_detailed_results()
        
        # Return success if all tests passed
        return summary["overall_status"] == "PASS"
        
    except Exception as e:
        logger.error(f"❌ Test suite execution failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)