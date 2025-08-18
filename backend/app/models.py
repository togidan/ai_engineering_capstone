"""
Shared Pydantic models for the application
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Knowledge Base Models
class SearchRequest(BaseModel):
    query: str
    k: int = 5
    filters: Optional[Dict[str, str]] = None

class SearchHit(BaseModel):
    doc_id: int
    title: str
    jurisdiction: Optional[str]
    industry: Optional[str]
    doc_type: Optional[str]
    source_url: Optional[str]
    file_path: str
    text: str
    score: float

class SearchResponse(BaseModel):
    hits: List[SearchHit]
    out_of_scope: bool

class UploadResponse(BaseModel):
    doc_id: int
    file_path: str
    filename: str
    file_size: int
    file_type: str
    description: str
    chunk_count: int

# RAG Models  
class IngestRequest(BaseModel):
    title: str
    content: str
    jurisdiction: Optional[str] = None
    industry: Optional[str] = None
    doc_type: Optional[str] = None
    source_url: Optional[str] = None

class IngestResponse(BaseModel):
    doc_id: int
    chunk_count: int
    auto_metadata: Dict[str, Any]

# RFI Models
class Citation(BaseModel):
    title: str
    source_url: Optional[str]
    file_path: str
    excerpt: str

class DraftRequest(BaseModel):
    company_name: str
    project_description: str
    requirements: List[str]
    
class DraftResponse(BaseModel):
    draft: str
    citations: List[Citation] = []