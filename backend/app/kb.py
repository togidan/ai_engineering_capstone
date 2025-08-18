from fastapi import APIRouter, UploadFile, File, HTTPException, Path, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any, List, Optional
import os
import logging
import shutil
from pathlib import Path as PathLib

from app.db import db_service
from app.milvus_utils import milvus_service
from app.text_utils import text_processor
from app.file_service import file_service
from app.llm_metadata_service import llm_metadata_service
from app.models import SearchRequest, SearchHit, SearchResponse, UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    industry: Optional[str] = None,
    doc_type: Optional[str] = None,
    source_url: Optional[str] = None
):
    """Upload and process a document with auto-metadata enrichment"""
    
    # Validate file format
    if not file_service.is_supported_format(file.filename or ""):
        supported_formats = ", ".join(file_service.supported_formats)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {supported_formats}"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Check file size (10MB limit)
        if len(file_content) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="File too large. Maximum size is 10MB."
            )
        
        # Extract text
        extracted_text = file_service.extract_text(file_content, file.filename or "")
        
        if not extracted_text or not extracted_text.strip():
            raise HTTPException(
                status_code=422,
                detail="No text content found in file"
            )
        
        # Generate metadata using LLM
        try:
            llm_metadata = llm_metadata_service.generate_metadata(
                text=extracted_text,
                filename=file.filename or "unknown"
            )
        except Exception as e:
            logger.error(f"LLM metadata generation failed: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Unable to generate document metadata: {str(e)}. Please ensure the document content is readable and try again."
            )
        
        # Prepare final metadata with actual file size and LLM-generated content
        actual_file_size = len(file_content)
        final_metadata = {
            "name": title or llm_metadata["name"],
            "description": llm_metadata["description"],
            "file_size": actual_file_size,
            "file_type": file.content_type or "application/octet-stream",
            "original_filename": file.filename or "unknown"
        }
        
        # Generate chunks
        chunks = text_processor.chunk_text(extracted_text)
        
        # Basic validation - ensure we have meaningful content
        if not chunks or len(chunks) == 0:
            raise HTTPException(
                status_code=422,
                detail="Document too short or could not be processed into searchable chunks"
            )
        
        # Save file to storage
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "kb")
        os.makedirs(data_dir, exist_ok=True)
        
        # Generate unique filename
        original_name = PathLib(file.filename or "document").stem
        file_extension = PathLib(file.filename or "document.txt").suffix
        file_path = os.path.join(data_dir, f"{original_name}_{hash(extracted_text) % 10000}{file_extension}")
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Insert document into database
        doc_id = db_service.insert_document(
            path=file_path,
            name=final_metadata["name"],
            file_size=final_metadata["file_size"],
            description=final_metadata["description"]
        )
        
        if not doc_id:
            raise HTTPException(status_code=500, detail="Failed to save document to database")
        
        # Insert chunks
        chunk_ids = db_service.insert_chunks(doc_id, chunks)
        
        if not chunk_ids:
            raise HTTPException(status_code=500, detail="Failed to save chunks to database")
        
        # Prepare data for Milvus insertion - use simplified metadata
        chunks_data = []
        for i, (chunk_id, chunk_text) in enumerate(zip(chunk_ids, chunks)):
            chunks_data.append({
                "primary_key": chunk_id,
                "text": chunk_text,
                "jurisdiction": "",  # No longer extracted
                "industry": "",     # No longer extracted  
                "doc_type": ""      # No longer extracted
            })
        
        # Insert into Milvus
        if milvus_service.is_available():
            pks = milvus_service.insert_chunks(chunks_data)
            if pks:
                # Update chunk records with milvus_pk from Milvus
                for chunk_id, pk in zip(chunk_ids, pks):
                    db_service.update_chunk_milvus_pk(chunk_id, int(pk))
            else:
                logger.warning(f"Failed to insert chunks into Milvus for doc {doc_id}")
        else:
            logger.warning("Milvus not available - chunks not indexed for search")
        
        logger.info(f"Successfully uploaded document {doc_id}: {final_metadata['name']}")
        
        return UploadResponse(
            doc_id=doc_id,
            file_path=file_path,
            filename=final_metadata["original_filename"],
            file_size=final_metadata["file_size"],
            file_type=final_metadata["file_type"],
            description=final_metadata["description"],
            chunk_count=len(chunks)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

@router.post("/search", response_model=SearchResponse)
@limiter.limit("10/minute")
async def search_knowledge_base(request: Request, payload: SearchRequest):
    """Search knowledge base with hybrid approach"""
    
    # Domain guard - validate query contains economic development terms
    if not text_processor.validate_domain_query(payload.query):
        return SearchResponse(
            hits=[],
            out_of_scope=True
        )
    
    if not milvus_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="Vector search service not available"
        )
    
    try:
        # Perform vector search in Milvus
        milvus_hits = milvus_service.search_similar(
            query_text=payload.query,
            k=payload.k * 2,  # Get more for re-ranking
            filters=payload.filters
        )
        
        if not milvus_hits:
            return SearchResponse(hits=[], out_of_scope=False)
        
        # Get chunk details from database
        milvus_pks = [hit["primary_key"] for hit in milvus_hits]
        chunks_data = db_service.get_chunks_by_milvus_pks(milvus_pks)
        
        # Create lookup for chunk data
        chunk_lookup = {chunk["milvus_pk"]: chunk for chunk in chunks_data}
        
        # Build response hits with re-ranking
        hits = []
        for milvus_hit in milvus_hits:
            chunk_data = chunk_lookup.get(milvus_hit["primary_key"])
            if not chunk_data:
                continue
            
            # Calculate keyword overlap for re-ranking
            keyword_overlap = text_processor.calculate_keyword_overlap(
                payload.query, 
                chunk_data["text"]
            )
            
            # Simple re-ranking: 85% cosine + 15% keyword overlap
            cosine_score = milvus_hit["score"]
            final_score = 0.85 * cosine_score + 0.15 * keyword_overlap
            
            # Truncate text for response
            text_snippet = chunk_data["text"][:1200]
            if len(chunk_data["text"]) > 1200:
                text_snippet += "..."
            
            hits.append(SearchHit(
                doc_id=chunk_data["doc_id"],
                title=chunk_data["title"] or "Untitled",
                jurisdiction=chunk_data.get("jurisdiction", ""),  # Default empty for simplified schema
                industry=chunk_data.get("industry", ""),         # Default empty for simplified schema
                doc_type=chunk_data.get("doc_type", ""),         # Default empty for simplified schema
                source_url=chunk_data.get("source_url", ""),     # Default empty for simplified schema
                file_path=chunk_data["path"],
                text=text_snippet,
                score=final_score
                # TODO: Restore full metadata when schema is expanded
                # jurisdiction=chunk_data["jurisdiction"],
                # industry=chunk_data["industry"],
                # doc_type=chunk_data["doc_type"],
                # source_url=chunk_data["source_url"],
            ))
        
        # Sort by final score and return top k
        hits.sort(key=lambda x: x.score, reverse=True)
        hits = hits[:payload.k]
        
        logger.info(f"Search for '{payload.query}' returned {len(hits)} hits")
        
        return SearchResponse(
            hits=hits,
            out_of_scope=False
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/doc/{doc_id}")
async def get_document(doc_id: int):
    """Get document metadata and file path"""
    
    doc = db_service.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found"
        )
    
    return {
        "doc_id": doc["id"],
        "title": doc.get("name", "Untitled"),  # Use 'name' field from simplified schema
        "description": doc.get("description", ""),  # Use 'description' field from simplified schema
        "file_size": doc.get("file_size", 0),  # Use 'file_size' field from simplified schema
        "file_path": doc["path"],
        "created_at": doc["created_at"]
        # TODO: Restore full metadata when schema is expanded
        # "jurisdiction": doc["jurisdiction"],
        # "industry": doc["industry"],
        # "doc_type": doc["doc_type"],
        # "source_url": doc["source_url"],
        # "summary": doc["summary"],
        # "keywords": doc["keywords"]
    }

@router.get("/read_file")
async def read_file(file_path: str):
    """Read file content for AI agent access"""
    
    # Security: ensure file path is within kb directory
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "kb")
    abs_data_dir = os.path.abspath(data_dir)
    abs_file_path = os.path.abspath(file_path)
    
    if not abs_file_path.startswith(abs_data_dir):
        raise HTTPException(
            status_code=403,
            detail="Access denied: file outside knowledge base directory"
        )
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="File not found"
        )
    
    try:
        # Use file service to extract text
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        filename = os.path.basename(file_path)
        extracted_text = file_service.extract_text(file_content, filename)
        
        if not extracted_text:
            raise HTTPException(
                status_code=422,
                detail="Could not extract text from file"
            )
        
        return {
            "file_path": file_path,
            "filename": filename,
            "content": extracted_text,
            "char_count": len(extracted_text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read file: {str(e)}"
        )

@router.get("/stats")
async def get_knowledge_base_stats():
    """Get knowledge base statistics"""
    
    # Get database stats
    db_stats = db_service.get_database_stats()
    
    # Get Milvus stats
    milvus_stats = milvus_service.get_collection_stats() if milvus_service.is_available() else {"error": "Milvus not available"}
    
    return {
        "database": db_stats,
        "milvus": milvus_stats,
        "services": {
            "milvus_available": milvus_service.is_available(),
            "embeddings_available": milvus_service.openai_client is not None
        }
    }

@router.post("/bootstrap")
@limiter.limit("1/minute")
async def bootstrap_demo_data(request: Request):
    """Bootstrap knowledge base with demo data"""
    try:
        logger.info("Starting knowledge base bootstrap...")
        
        # Run the simple demo ingest
        import sys
        import subprocess
        from pathlib import Path
        
        # Get the scripts directory
        backend_dir = Path(__file__).parent.parent
        script_path = backend_dir / "scripts" / "simple_demo_ingest.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=404, detail="Bootstrap script not found")
        
        # Run the script
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, cwd=str(backend_dir), timeout=300)  # 5 minute timeout
        
        logger.info(f"Bootstrap script stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Bootstrap script stderr: {result.stderr}")
        
        if result.returncode != 0:
            logger.error(f"Bootstrap failed with return code {result.returncode}")
            logger.error(f"Bootstrap stderr: {result.stderr}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "Bootstrap script failed",
                    "return_code": result.returncode,
                    "stderr": result.stderr[:1000],  # Limit error message length
                    "stdout": result.stdout[:1000] if result.stdout else ""
                }
            )
        
        # Get updated stats
        db_stats = db_service.get_database_stats()
        
        logger.info("Knowledge base bootstrap completed successfully")
        logger.info(f"Final stats: {db_stats}")
        
        return {
            "message": "Demo data loaded successfully",
            "status": "completed",
            "stats": db_stats,
            "stdout": result.stdout[-500:] if result.stdout else "",  # Last 500 chars of output
        }
        
    except Exception as e:
        logger.error(f"Bootstrap error: {e}")
        raise HTTPException(status_code=500, detail=f"Bootstrap failed: {str(e)}")

# Agent-specific endpoints
@router.get("/agent/document/{doc_id}")
async def agent_read_document(doc_id: int):
    """Agent endpoint: Read full document content by ID"""
    from app.agent_service import agent_service
    
    document = agent_service.read_document_by_id(doc_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document {doc_id} not found or not accessible"
        )
    
    return document

@router.get("/agent/read_path")
async def agent_read_by_path(file_path: str):
    """Agent endpoint: Read document content by file path"""
    from app.agent_service import agent_service
    
    document = agent_service.read_document_by_path(file_path)
    if not document:
        raise HTTPException(
            status_code=404,
            detail="File not found or not accessible"
        )
    
    return document

@router.post("/agent/search_and_read")
async def agent_search_and_read(request: SearchRequest):
    """Agent endpoint: Search KB and return full document content"""
    from app.agent_service import agent_service
    
    # Domain guard
    if not text_processor.validate_domain_query(request.query):
        raise HTTPException(
            status_code=400,
            detail="Query outside economic development domain scope"
        )
    
    results = await agent_service.search_and_read(
        query=request.query,
        filters=request.filters,
        k=request.k
    )
    
    return {
        "query": request.query,
        "results": results,
        "result_count": len(results)
    }

@router.get("/agent/list_documents")
async def agent_list_documents(
    jurisdiction: Optional[str] = None,
    industry: Optional[str] = None,
    doc_type: Optional[str] = None,
    limit: int = 20
):
    """Agent endpoint: List available documents with metadata"""
    from app.agent_service import agent_service
    
    documents = agent_service.get_document_list(
        jurisdiction=jurisdiction,
        industry=industry,
        doc_type=doc_type,
        limit=limit
    )
    
    return {
        "documents": documents,
        "total_count": len(documents),
        "filters_applied": {
            "jurisdiction": jurisdiction,
            "industry": industry,
            "doc_type": doc_type
        }
    }

@router.get("/agent/knowledge_summary")
async def agent_knowledge_summary():
    """Agent endpoint: Get summary of available knowledge base content"""
    from app.agent_service import agent_service
    
    summary = agent_service.get_knowledge_summary()
    
    return {
        "knowledge_base_summary": summary,
        "agent_capabilities": {
            "search_and_read": "Search documents and get full content",
            "read_by_id": "Read specific document by ID",
            "read_by_path": "Read document by file path",
            "list_documents": "Browse available documents with filters",
            "domain_focus": "Economic development, city data, incentives, workforce"
        },
        "usage_notes": [
            "All document access is read-only",
            "File paths are restricted to knowledge base directory",
            "Search queries must be related to economic development",
            "Full document content is returned for comprehensive analysis"
        ]
    }

@router.get("/quality/report")
async def get_quality_report():
    """Generate quality report for the knowledge base"""
    
    try:
        # Get all documents for staleness check
        documents = db_service.search_documents(limit=1000)
        
        # Check staleness
        staleness_report = quality_service.check_knowledge_base_staleness(documents)
        
        # Get database stats
        db_stats = db_service.get_database_stats()
        
        # Calculate quality metrics
        embedding_coverage = db_stats.get("embedding_coverage", 0)
        total_docs = db_stats.get("documents", 0)
        
        quality_score = 100
        issues = []
        recommendations = []
        
        # Embedding coverage check
        if embedding_coverage < 0.95:
            quality_score -= 20
            issues.append(f"Low embedding coverage: {embedding_coverage*100:.1f}% (target: ≥95%)")
            recommendations.append("Re-index documents with missing embeddings")
        
        # Staleness check
        stale_percentage = (staleness_report["stale_documents"] / max(total_docs, 1)) * 100
        if stale_percentage > 30:
            quality_score -= 25
            issues.append(f"High staleness: {stale_percentage:.1f}% of documents are stale")
            recommendations.extend(staleness_report["recommendations"])
        elif stale_percentage > 15:
            quality_score -= 10
            recommendations.extend(staleness_report["recommendations"])
        
        # Data volume check
        if total_docs < 10:
            quality_score -= 15
            issues.append("Low document count for meaningful analysis")
            recommendations.append("Add more diverse economic development content")
        
        report = {
            "timestamp": staleness_report,
            "overall_quality_score": max(quality_score, 0),
            "status": "good" if quality_score >= 80 else "needs_attention" if quality_score >= 60 else "poor",
            "database_stats": db_stats,
            "staleness_analysis": staleness_report,
            "issues": issues,
            "recommendations": recommendations,
            "metrics": {
                "embedding_coverage": embedding_coverage,
                "stale_percentage": stale_percentage,
                "total_documents": total_docs
            }
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Quality report generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate quality report: {str(e)}"
        )