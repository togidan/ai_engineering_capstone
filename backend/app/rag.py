from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Dict, Any, List, Optional
import logging

from app.models import SearchRequest, SearchResponse, IngestRequest, IngestResponse
from app.db import db_service
from app.text_utils import text_processor

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/search", response_model=SearchResponse)
@limiter.limit("10/minute")
async def rag_search(request: Request, payload: SearchRequest):
    """
    RAG search endpoint - wraps knowledge base search for public data sources
    Focuses on Wikipedia and other public economic development data
    """
    # Import locally to avoid circular import
    from app.kb import search_knowledge_base

    # Pass parameters with correct names: request (Request), payload (SearchRequest)
    return await search_knowledge_base(request=request, payload=payload)


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("10/minute")
async def ingest_content(request: Request, payload: IngestRequest):
    """
    Bulk ingest capability for structured content (like Wikipedia articles)
    The HTTP Request is `request` and the body is `payload`
    """
    try:
        # Auto-extract metadata from content
        auto_metadata = text_processor.extract_metadata(payload.content, payload.title)

        # Use provided metadata or fall back to auto-extracted
        final_metadata = {
            "title": payload.title,
            "jurisdiction": payload.jurisdiction or auto_metadata.get("jurisdiction"),
            "industry": payload.industry or auto_metadata.get("industry"),
            "doc_type": payload.doc_type or auto_metadata.get("doc_type"),
            "source_url": payload.source_url,
            "keywords": auto_metadata.get("keywords"),
            "summary": auto_metadata.get("summary")
        }

        # Generate chunks
        chunks = text_processor.chunk_text(payload.content)

        # Data quality validation
        quality_check = text_processor.validate_document_quality(payload.content, chunks)
        if not quality_check.get("passed", False):
            raise HTTPException(
                status_code=422,
                detail=f"Content quality check failed: {quality_check}"
            )

        # For ingested content, we don't save files - just store virtual path
        virtual_path = f"/virtual/{payload.title.replace(' ', '_').lower()}"

        # Insert document into database with simplified schema
        # TODO: Restore full metadata schema if needed in the future
        # doc_id = db_service.insert_document(
        #     path=virtual_path,
        #     title=final_metadata["title"],
        #     jurisdiction=final_metadata["jurisdiction"],
        #     industry=final_metadata["industry"],
        #     doc_type=final_metadata["doc_type"],
        #     source_url=final_metadata["source_url"],
        #     keywords=final_metadata["keywords"],
        #     summary=final_metadata["summary"]
        # )
        
        # Current simplified schema:
        doc_id = db_service.insert_document(
            path=virtual_path,
            name=final_metadata["title"],
            file_size=len(payload.content.encode('utf-8')),  # Size in bytes
            description=final_metadata["summary"] or f"Economic development content: {final_metadata['title']}"
        )

        if not doc_id:
            raise HTTPException(status_code=500, detail="Failed to save content to database")

        # Insert chunks
        chunk_ids = db_service.insert_chunks(doc_id, chunks)

        if not chunk_ids:
            raise HTTPException(status_code=500, detail="Failed to save chunks to database")

        # Prepare data for Milvus insertion
        from app.milvus_utils import milvus_service

        chunks_data = []
        for chunk_id, chunk_text in zip(chunk_ids, chunks):
            chunks_data.append({
                # Use simplified metadata for Milvus (matches kb.py structure)
                "text": chunk_text,
                "jurisdiction": "",  # Simplified schema - no jurisdiction tracking
                "industry": "",     # Simplified schema - no industry tracking  
                "doc_type": ""      # Simplified schema - no doc_type tracking
                # TODO: Restore full metadata when schema is expanded
                # "jurisdiction": final_metadata["jurisdiction"] or "",
                # "industry": final_metadata["industry"] or "",
                # "doc_type": final_metadata["doc_type"] or ""
            })

        # Insert into Milvus
        if milvus_service.is_available():
            pks = milvus_service.insert_chunks(chunks_data)
            if pks:
                # Update chunk records with milvus_pk values returned by Milvus
                for chunk_id, pk in zip(chunk_ids, pks):
                    db_service.update_chunk_milvus_pk(chunk_id, int(pk))
            else:
                logger.warning(f"Failed to insert chunks into Milvus for doc {doc_id}")
        else:
            logger.warning("Milvus not available - chunks not indexed for search")

        logger.info(f"Successfully ingested content: {payload.title}")

        return IngestResponse(
            doc_id=doc_id,
            chunk_count=len(chunks),
            auto_metadata=auto_metadata
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest content: {str(e)}"
        )


@router.get("/stats")
async def get_rag_stats():
    """Get RAG system statistics"""

    # Get database stats filtered for public data sources
    db_stats = db_service.get_database_stats()

    # Count documents by source
    virtual_docs = len([d for d in db_service.search_documents(limit=1000) if d["path"].startswith("/virtual/")])
    file_docs = db_stats["documents"] - virtual_docs

    return {
        "total_documents": db_stats["documents"],
        "virtual_documents": virtual_docs,
        "file_documents": file_docs,
        "total_chunks": db_stats["chunks"],
        "indexed_chunks": db_stats["indexed_chunks"],
        "embedding_coverage": db_stats["embedding_coverage"]
        # TODO: Restore metadata breakdowns when schema is expanded
        # "top_jurisdictions": db_stats["top_jurisdictions"],
        # "top_industries": db_stats["top_industries"]
    }
