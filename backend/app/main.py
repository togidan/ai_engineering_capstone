from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
import os
from dotenv import load_dotenv
from app.rfi import router as rfi_router
from app.kb import router as kb_router
from app.rag import router as rag_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="City Opportunity RAG MVP API",
    description="API for city opportunity scoring, RFP analysis, and RAG knowledge base",
    version="2.0.0"
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://localhost:5173",
        "https://ai-engineering-capstone-1.onrender.com",  # Explicit frontend URL
        "*"  # Allow all origins for deployment (remove for production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rfi_router, prefix="/rfi", tags=["RFI"])
app.include_router(kb_router, prefix="/kb", tags=["Knowledge Base"])
app.include_router(rag_router, prefix="/rag", tags=["RAG"])

@app.get("/")
async def root():
    from app.llm_service import llm_service
    from app.milvus_utils import milvus_service
    from app.db import db_service
    
    # Get system status
    db_stats = db_service.get_database_stats()
    
    return {
        "message": "City Opportunity RAG MVP API", 
        "version": "2.0.0",
        "database_info": {
            "type": "PostgreSQL" if db_service.use_postgres else "SQLite",
            "url_provided": bool(db_service.postgres_url) if hasattr(db_service, 'postgres_url') else False
        },
        "services": {
            "llm_available": llm_service.is_available(),
            "milvus_available": milvus_service.is_available(),
            "database_available": True
        },
        "features": {
            "city_scoring": "Client-side CSV/JSON analysis",
            "rfp_analysis": "LLM + regex fallback + KB integration",
            "draft_generation": "LLM + KB context + citations",
            "knowledge_base": "Vector search with metadata filters",
            "rag_search": "Hybrid search with re-ranking"
        },
        "stats": {
            "documents": db_stats.get("documents", 0),
            "chunks": db_stats.get("chunks", 0),
            "indexed_chunks": db_stats.get("indexed_chunks", 0)
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.milvus_utils import milvus_service
    
    return {
        "status": "healthy",
        "services": {
            "database": "healthy",
            "milvus": "healthy" if milvus_service.is_available() else "unavailable",
            "embeddings": "healthy" if milvus_service.openai_client else "unavailable"
        }
    }