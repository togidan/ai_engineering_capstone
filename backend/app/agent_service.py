"""
Agent Service - Helper functions for AI agents to interact with the knowledge base
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from app.db import db_service
from app.file_service import file_service
from app.models import SearchRequest

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "kb")
        
    def read_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """
        Read full document content by document ID
        Returns document metadata and extracted text content
        """
        try:
            # Get document metadata
            doc = db_service.get_document(doc_id)
            if not doc:
                logger.error(f"Document {doc_id} not found")
                return None
            
            # Check if file exists
            file_path = doc["path"]
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Extract text content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            extracted_text = file_service.extract_text(file_content, filename)
            
            if not extracted_text:
                logger.error(f"Could not extract text from {file_path}")
                return None
            
            return {
                "doc_id": doc["id"],
                "title": doc["title"],
                "jurisdiction": doc["jurisdiction"],
                "industry": doc["industry"],
                "doc_type": doc["doc_type"],
                "source_url": doc["source_url"],
                "file_path": file_path,
                "content": extracted_text,
                "summary": doc["summary"],
                "keywords": doc["keywords"],
                "created_at": doc["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Failed to read document {doc_id}: {e}")
            return None
    
    def read_document_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Read document content by file path with security checks
        """
        try:
            # Security: ensure file path is within kb directory
            abs_data_dir = os.path.abspath(self.data_dir)
            abs_file_path = os.path.abspath(file_path)
            
            if not abs_file_path.startswith(abs_data_dir):
                logger.error(f"Access denied: file outside KB directory: {file_path}")
                return None
            
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Extract text content
            with open(file_path, "rb") as f:
                file_content = f.read()
            
            filename = os.path.basename(file_path)
            extracted_text = file_service.extract_text(file_content, filename)
            
            if not extracted_text:
                logger.error(f"Could not extract text from {file_path}")
                return None
            
            # Try to find document metadata
            doc_metadata = None
            try:
                # Query database for document with this path
                from app.db import db_service
                import sqlite3
                
                with sqlite3.connect(db_service.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.execute("SELECT * FROM documents WHERE path = ?", (file_path,))
                    row = cursor.fetchone()
                    if row:
                        doc_metadata = dict(row)
            except Exception as e:
                logger.warning(f"Could not fetch metadata for {file_path}: {e}")
            
            result = {
                "file_path": file_path,
                "filename": filename,
                "content": extracted_text,
                "char_count": len(extracted_text)
            }
            
            # Add metadata if available
            if doc_metadata:
                result.update({
                    "doc_id": doc_metadata["id"],
                    "title": doc_metadata["title"],
                    "jurisdiction": doc_metadata["jurisdiction"],
                    "industry": doc_metadata["industry"],
                    "doc_type": doc_metadata["doc_type"],
                    "source_url": doc_metadata["source_url"],
                    "summary": doc_metadata["summary"],
                    "keywords": doc_metadata["keywords"]
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    async def search_and_read(self, query: str, filters: Optional[Dict[str, str]] = None, k: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base and return full document content for top results
        Useful for agents that need comprehensive context
        """
        try:
            # Import locally to avoid circular import
            from app.kb import search_knowledge_base
            
            # Perform search
            search_req = SearchRequest(query=query, k=k, filters=filters)
            
            # Mock request object for rate limiting
            class MockRequest:
                client = type('Client', (), {'host': '127.0.0.1'})()
            
            mock_request = MockRequest()
            search_response = await search_knowledge_base(mock_request, search_req)
            
            if search_response.out_of_scope or not search_response.hits:
                return []
            
            # Read full content for each hit
            results = []
            for hit in search_response.hits:
                doc_content = self.read_document_by_id(hit.doc_id)
                if doc_content:
                    # Add search score and snippet
                    doc_content["search_score"] = hit.score
                    doc_content["search_snippet"] = hit.text
                    results.append(doc_content)
            
            return results
            
        except Exception as e:
            logger.error(f"Search and read failed: {e}")
            return []
    
    def get_document_list(
        self, 
        jurisdiction: str = None, 
        industry: str = None, 
        doc_type: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get list of available documents with metadata
        Useful for agents to browse available knowledge
        """
        try:
            documents = db_service.search_documents(
                jurisdiction=jurisdiction,
                industry=industry,
                doc_type=doc_type,
                limit=limit
            )
            
            # Add file existence check
            available_docs = []
            for doc in documents:
                if os.path.exists(doc["path"]):
                    available_docs.append({
                        "doc_id": doc["id"],
                        "title": doc["title"],
                        "jurisdiction": doc["jurisdiction"],
                        "industry": doc["industry"],
                        "doc_type": doc["doc_type"],
                        "source_url": doc["source_url"],
                        "file_path": doc["path"],
                        "summary": doc["summary"],
                        "created_at": doc["created_at"]
                    })
            
            return available_docs
            
        except Exception as e:
            logger.error(f"Failed to get document list: {e}")
            return []
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """
        Get summary of available knowledge base content
        Useful for agents to understand scope of available information
        """
        try:
            stats = db_service.get_database_stats()
            
            # Get breakdown by categories
            docs_by_jurisdiction = stats.get("top_jurisdictions", [])
            docs_by_industry = stats.get("top_industries", [])
            
            return {
                "total_documents": stats.get("documents", 0),
                "total_chunks": stats.get("chunks", 0),
                "indexed_chunks": stats.get("indexed_chunks", 0),
                "embedding_coverage": stats.get("embedding_coverage", 0),
                "top_jurisdictions": docs_by_jurisdiction[:5],
                "top_industries": docs_by_industry[:5],
                "capabilities": [
                    "Economic development document analysis",
                    "City and regional data",
                    "Incentive and policy information",
                    "Workforce and infrastructure data",
                    "Case studies and best practices"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get knowledge summary: {e}")
            return {}

# Global agent service instance
agent_service = AgentService()