from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Union

class RequirementLogic(BaseModel):
    threshold_min: Optional[Union[int, float]] = None
    threshold_max: Optional[Union[int, float]] = None
    options: Optional[List[str]] = None
    format: Optional[str] = None

class RequirementRow(BaseModel):
    id: str
    section: str
    priority: str
    requirement_text: str
    normalized_key: Optional[str] = None
    datatype: str
    unit: Optional[str] = None
    logic: Optional[RequirementLogic] = None
    answer_value: Optional[str] = None
    status: str  # 'met' | 'not_met' | 'unknown'
    source_field: Optional[str] = None
    source_attachment: Optional[str] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None

class AnalyzeSummary(BaseModel):
    met: int
    not_met: int
    unknown: int
    critical_gaps: List[str]
    data_sources_used: List[str]

class AnalyzeRequest(BaseModel):
    rfp_text: str
    features: Dict[str, Any]

class AnalyzeResponse(BaseModel):
    requirements_table: List[RequirementRow]
    summary: AnalyzeSummary
    analysis_method: str = "regex"  # "llm" or "regex"

class Citation(BaseModel):
    title: str
    source_url: Optional[str] = None
    file_path: str
    excerpt: str

class DraftSection(BaseModel):
    heading: str
    content: str

class DraftRequest(BaseModel):
    rfp_text: str
    features: Dict[str, Any]
    city: Optional[str] = None
    industry: Optional[str] = None

class DraftResponse(BaseModel):
    sections: List[DraftSection]
    citations: List[Citation] = []
    generation_method: str = "deterministic"  # "llm" or "deterministic"
    kb_context_used: bool = False