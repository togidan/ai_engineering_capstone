from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
import re
import json
import os
import logging
from typing import Dict, Any, List, Union
from app.schemas import (
    AnalyzeRequest, AnalyzeResponse, RequirementRow, RequirementLogic, AnalyzeSummary,
    DraftRequest, DraftResponse, DraftSection, Citation
)
from app.llm_service import llm_service
from app.file_service import file_service

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

def sanitize_llm_output(obj: Any) -> Any:
    """
    Recursively sanitize LLM output to ensure type compatibility with Pydantic models.
    Converts boolean values to strings to handle cases where LLM returns [true, false]
    instead of ["true", "false"] for options fields.
    """
    if isinstance(obj, dict):
        return {k: sanitize_llm_output(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_llm_output(i) for i in obj]
    # Convert bools to strings so Pydantic expecting str will accept them
    if isinstance(obj, bool):
        return str(obj)  # True -> "True", False -> "False"
    return obj

def load_keymap() -> Dict[str, Any]:
    """Load regex patterns for fallback parsing"""
    keymap_path = os.path.join(os.path.dirname(__file__), "config", "keymap.json")
    try:
        with open(keymap_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "patterns": {
                "budget": r"budget.*?(\$[\d,]+(?:\.\d+)?[kmb]?)",
                "timeline": r"(?:deadline|timeline|due).*?(\d+\s+(?:days?|weeks?|months?))",
                "location": r"(?:location|site|facility).*?([A-Z][a-z]+,?\s*[A-Z]{2})",
                "employees": r"(?:employees?|staff|workforce).*?(\d+)",
                "square_feet": r"(\d+(?:,\d+)?)\s*(?:sq\.?\s*ft\.?|square\s+feet)"
            },
            "requirements": {
                "technical": ["technology", "system", "software", "hardware", "network"],
                "operational": ["process", "workflow", "procedure", "operation"],
                "financial": ["budget", "cost", "price", "payment", "funding"],
                "timeline": ["deadline", "schedule", "timeline", "duration"]
            }
        }

def llm_to_pydantic(llm_response: Dict[str, Any]) -> tuple[List[RequirementRow], AnalyzeSummary]:
    """Convert LLM JSON response to Pydantic models"""
    # Sanitize the LLM response to ensure type compatibility
    sanitized_response = sanitize_llm_output(llm_response)
    
    requirements = []
    
    for req_data in sanitized_response.get("requirements_table", []):
        # Extract logic object if present
        logic = None
        if "logic" in req_data and req_data["logic"]:
            logic = RequirementLogic(
                threshold_min=req_data["logic"].get("threshold_min"),
                threshold_max=req_data["logic"].get("threshold_max"),
                options=req_data["logic"].get("options"),
                format=req_data["logic"].get("format")
            )
        
        requirement = RequirementRow(
            id=req_data.get("id", f"req_{len(requirements) + 1}"),
            section=req_data.get("section", "General"),
            priority=req_data.get("priority", "medium").lower(),
            requirement_text=req_data.get("requirement_text", ""),
            normalized_key=req_data.get("normalized_key"),
            datatype=req_data.get("datatype", "text"),
            unit=req_data.get("unit"),
            logic=logic,
            answer_value=req_data.get("answer_value"),
            status=req_data.get("status", "unknown").lower().replace(" ", "_"),
            source_field=req_data.get("source_field"),
            source_attachment=req_data.get("source_attachment"),
            confidence=req_data.get("confidence", 0.0),
            notes=req_data.get("notes")
        )
        requirements.append(requirement)
    
    # Extract summary (using sanitized response)
    summary_data = sanitized_response.get("summary", {})
    summary = AnalyzeSummary(
        met=summary_data.get("met", 0),
        not_met=summary_data.get("not_met", 0),
        unknown=summary_data.get("unknown", 0),
        critical_gaps=summary_data.get("critical_gaps", []),
        data_sources_used=summary_data.get("data_sources_used", [])
    )
    
    return requirements, summary

def extract_requirements_fallback(rfp_text: str, features: Dict[str, Any]) -> List[RequirementRow]:
    """Fallback regex-based parsing (original method)"""
    keymap = load_keymap()
    requirements = []
    
    # Simple regex-based parsing
    budget_match = re.search(keymap["patterns"]["budget"], rfp_text, re.IGNORECASE)
    timeline_match = re.search(keymap["patterns"]["timeline"], rfp_text, re.IGNORECASE)
    location_match = re.search(keymap["patterns"]["location"], rfp_text, re.IGNORECASE)
    
    req_id = 1
    
    if budget_match:
        budget_value = budget_match.group(1)
        status = "met" if "budget" in features else "unknown"
        requirements.append(RequirementRow(
            id=f"req_{req_id}",
            section="Financial",
            priority="high",
            requirement_text=f"Budget requirement: {budget_value}",
            normalized_key="budget",
            datatype="currency",
            unit="USD",
            answer_value=str(features.get("budget", "TODO")),
            status=status,
            source_field="budget" if "budget" in features else None,
            notes="Extracted from RFP text"
        ))
        req_id += 1
    
    if timeline_match:
        timeline_value = timeline_match.group(1)
        status = "met" if "timeline" in features else "unknown"
        requirements.append(RequirementRow(
            id=f"req_{req_id}",
            section="Schedule",
            priority="high",
            requirement_text=f"Timeline requirement: {timeline_value}",
            normalized_key="timeline",
            datatype="duration",
            unit="days",
            answer_value=str(features.get("timeline", "TODO")),
            status=status,
            source_field="timeline" if "timeline" in features else None,
            notes="Extracted from RFP text"
        ))
        req_id += 1
    
    if location_match:
        location_value = location_match.group(1)
        status = "met" if "location" in features else "unknown"
        requirements.append(RequirementRow(
            id=f"req_{req_id}",
            section="Location",
            priority="medium",
            requirement_text=f"Location requirement: {location_value}",
            normalized_key="location",
            datatype="text",
            answer_value=str(features.get("location", "TODO")),
            status=status,
            source_field="location" if "location" in features else None,
            notes="Extracted from RFP text"
        ))
        req_id += 1
    
    # Add some default technical requirements
    for tech_word in ["technology", "software", "system"]:
        if tech_word.lower() in rfp_text.lower():
            requirements.append(RequirementRow(
                id=f"req_{req_id}",
                section="Technical",
                priority="high",
                requirement_text=f"Technical capability: {tech_word} solution required",
                normalized_key=f"tech_{tech_word}",
                datatype="boolean",
                answer_value=str(features.get(f"tech_{tech_word}", "TODO")),
                status="met" if f"tech_{tech_word}" in features else "unknown",
                source_field=f"tech_{tech_word}" if f"tech_{tech_word}" in features else None,
                notes="Inferred from RFP content"
            ))
            req_id += 1
    
    return requirements

def search_kb_for_context(request: DraftRequest) -> tuple[str, List[Citation]]:
    """Search knowledge base for relevant context and citations"""
    
    try:
        from app.kb import SearchRequest, search_knowledge_base
        from app.milvus_utils import milvus_service
        
        if not milvus_service.is_available():
            logger.info("Milvus not available - skipping KB search")
            return "", []
        
        # Build search query from RFP requirements
        search_terms = []
        if request.industry:
            search_terms.append(request.industry)
        if request.city:
            search_terms.append(request.city)
        
        # Extract key terms from RFP text
        rfp_lower = request.rfp_text.lower()
        if "incentive" in rfp_lower or "tax" in rfp_lower:
            search_terms.append("incentives")
        if "workforce" in rfp_lower or "employment" in rfp_lower:
            search_terms.append("workforce")
        if "infrastructure" in rfp_lower or "transport" in rfp_lower:
            search_terms.append("infrastructure")
        if "power" in rfp_lower or "utility" in rfp_lower:
            search_terms.append("infrastructure utilities")
        
        query = " ".join(search_terms) if search_terms else f"{request.industry or ''} economic development"
        
        # Build filters
        filters = {}
        if request.city:
            # Try to extract state from city string or use common mappings
            if "," in request.city:
                filters["jurisdiction"] = request.city
            else:
                # Common city-state mappings for major cities
                city_mappings = {
                    "columbus": "Columbus, OH",
                    "cleveland": "Cleveland, OH", 
                    "cincinnati": "Cincinnati, OH",
                    "new york": "New York, NY",
                    "los angeles": "Los Angeles, CA",
                    "chicago": "Chicago, IL"
                }
                city_key = request.city.lower()
                if city_key in city_mappings:
                    filters["jurisdiction"] = city_mappings[city_key]
        
        if request.industry:
            filters["industry"] = request.industry
        
        # Search knowledge base
        search_req = SearchRequest(
            query=query,
            k=5,
            filters=filters
        )
        
        # Mock request object for rate limiting
        class MockRequest:
            client = type('Client', (), {'host': '127.0.0.1'})()
        
        mock_request = MockRequest()
        
        # Import asyncio to run the async function
        import asyncio
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, this won't work
                # Fall back to no KB search
                logger.warning("Cannot run async KB search from sync context")
                return "", []
            else:
                search_response = loop.run_until_complete(search_knowledge_base(mock_request, search_req))
        except RuntimeError:
            # No event loop running, create one
            search_response = asyncio.run(search_knowledge_base(mock_request, search_req))
        
        if search_response.out_of_scope or not search_response.hits:
            logger.info("No relevant KB results found")
            return "", []
        
        # Build context and citations
        context_parts = []
        citations = []
        
        for hit in search_response.hits:
            # Add to context
            context_parts.append(f"Source: {hit.title}\n{hit.text}\n")
            
            # Create citation
            citation = Citation(
                title=hit.title,
                source_url=hit.source_url,
                file_path=hit.file_path,
                doc_type=hit.doc_type,
                jurisdiction=hit.jurisdiction
            )
            citations.append(citation)
        
        context = "\n---\n".join(context_parts)
        logger.info(f"Found {len(citations)} KB sources for context")
        
        return context, citations
        
    except Exception as e:
        logger.error(f"KB search failed: {e}")
        return "", []

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_rfp(request: AnalyzeRequest):
    """Analyze RFP using LLM first with KB context, fallback to regex parsing"""
    
    logger.info(f"Analyzing RFP: {len(request.rfp_text)} chars, {len(request.features)} features")
    
    # Search knowledge base for relevant context to inform analysis
    mock_draft_request = DraftRequest(
        rfp_text=request.rfp_text,
        features=request.features,
        city=request.features.get("city", ""),
        industry="economic development"  # Default industry for context search
    )
    
    kb_context, kb_citations = search_kb_for_context(mock_draft_request)
    if kb_context:
        logger.info(f"Using KB context for analysis: {len(kb_citations)} sources found")
    
    # Try LLM parsing first with KB context
    llm_response = llm_service.parse_rfp(request.rfp_text, request.features, "analyze", kb_context)
    
    if llm_response:
        try:
            requirements_table, summary = llm_to_pydantic(llm_response)
            logger.info(f"LLM analysis successful: {len(requirements_table)} requirements extracted")
            logger.debug(f"LLM analysis method: {'chunked' if len(request.rfp_text) > 8000 else 'single'}")
            
            return AnalyzeResponse(
                requirements_table=requirements_table,
                summary=summary,
                analysis_method="llm"
            )
        except Exception as e:
            logger.error(f"Failed to convert LLM response to Pydantic models: {e}")
            logger.debug(f"LLM response structure: {list(llm_response.keys()) if isinstance(llm_response, dict) else type(llm_response)}")
            # Fall through to regex parsing
    else:
        logger.warning("LLM parsing returned None - falling back to regex analysis")
    
    # Fallback to regex parsing
    logger.info("Using fallback regex analysis for RFP")
    requirements_table = extract_requirements_fallback(request.rfp_text, request.features)
    
    met_count = len([r for r in requirements_table if r.status == "met"])
    not_met_count = len([r for r in requirements_table if r.status == "not_met"])
    unknown_count = len([r for r in requirements_table if r.status == "unknown"])
    
    critical_gaps = [r.requirement_text for r in requirements_table if r.status == "not_met" and r.priority == "high"]
    data_sources_used = list(set([r.source_field for r in requirements_table if r.source_field]))
    
    summary = AnalyzeSummary(
        met=met_count,
        not_met=not_met_count,
        unknown=unknown_count,
        critical_gaps=critical_gaps,
        data_sources_used=data_sources_used
    )
    
    logger.info(f"Regex analysis completed: {len(requirements_table)} requirements ({met_count} met, {not_met_count} not met, {unknown_count} unknown)")
    
    return AnalyzeResponse(
        requirements_table=requirements_table,
        summary=summary,
        analysis_method="regex"
    )

def generate_draft_fallback(request: DraftRequest) -> List[DraftSection]:
    """Fallback deterministic draft generation (original method)"""
    sections = []
    
    # Executive Summary
    city_info = f" for {request.city}" if request.city else ""
    industry_info = f" in the {request.industry} sector" if request.industry else ""
    
    executive_summary = f"""We are pleased to submit this response to your RFP{city_info}{industry_info}. 
Our team has extensive experience delivering similar solutions and is well-positioned to meet your requirements. 
Based on our analysis, we can address {len([k for k in request.features.keys() if request.features[k] != 'TODO'])} of your key requirements immediately."""
    
    sections.append(DraftSection(
        heading="Executive Summary",
        content=executive_summary
    ))
    
    # Technical Approach
    tech_features = [k for k in request.features.keys() if k.startswith('tech_') and request.features[k] != 'TODO']
    if tech_features:
        tech_content = f"Our technical approach leverages proven capabilities in {', '.join(tech_features)}. "
        tech_content += "We follow industry best practices and can scale to meet your needs."
    else:
        tech_content = "We will develop a comprehensive technical approach tailored to your specific requirements."
    
    sections.append(DraftSection(
        heading="Technical Approach",
        content=tech_content
    ))
    
    # Project Management
    timeline = request.features.get('timeline', 'TBD')
    budget = request.features.get('budget', 'competitive pricing')
    
    pm_content = f"Timeline: {timeline}\nBudget: {budget}\n"
    pm_content += "We employ proven project management methodologies to ensure on-time, on-budget delivery."
    
    sections.append(DraftSection(
        heading="Project Management",
        content=pm_content
    ))
    
    # Qualifications
    qual_content = "Our team brings deep expertise and a track record of successful implementations. "
    qual_content += "We are committed to your success and look forward to partnering with you."
    
    sections.append(DraftSection(
        heading="Qualifications",
        content=qual_content
    ))
    
    return sections

@router.post("/draft", response_model=DraftResponse)
@limiter.limit("10/minute")
async def draft_rfi(request: Request, rfp: DraftRequest):
    """Generate RFI draft using LLM with KB context, fallback to deterministic generation"""
    # quick sanity check while debugging
    if not isinstance(request, Request):
        # this should never fire if FastAPI injects correctly
        raise RuntimeError("Injected `request` is not a starlette.requests.Request instance")

    logger.info(f"Generating draft: {len(rfp.rfp_text)} chars, {len(rfp.features)} features")
    
    # Search knowledge base for relevant context
    kb_context, citations = search_kb_for_context(rfp)
    kb_context_used = bool(kb_context)
    
    if kb_context_used:
        logger.info(f"Using KB context: {len(citations)} citations found")
    
    # Try LLM generation first with KB context
    llm_response = llm_service.parse_rfp(rfp.rfp_text, rfp.features, "draft", kb_context)
    
    if llm_response and "draft" in llm_response:
        try:
            draft_data = llm_response["draft"]
            if draft_data.get("enabled", False) and "sections" in draft_data:
                sections = [
                    DraftSection(
                        heading=section.get("heading", ""),
                        content=section.get("content", "")
                    )
                    for section in draft_data["sections"]
                ]
                logger.info(f"LLM draft generation successful: {len(sections)} sections")
                logger.debug(f"Draft method: {'chunked' if len(rfp.rfp_text) > 8000 else 'single'}")
                
                return DraftResponse(
                    sections=sections,
                    citations=citations,
                    generation_method="llm",
                    kb_context_used=kb_context_used
                )
            else:
                logger.warning(
                    "LLM draft disabled or missing sections: "
                    f"enabled={draft_data.get('enabled')}, has_sections={'sections' in draft_data}"
                )
        except Exception as e:
            logger.error(f"Failed to parse LLM draft response: {e}")
            logger.debug(
                f"Draft response structure: "
                f"{list(llm_response.keys()) if isinstance(llm_response, dict) else type(llm_response)}"
            )
            # Fall through to deterministic generation
    else:
        if llm_response:
            logger.warning("LLM response missing 'draft' section")
        else:
            logger.warning("LLM draft generation returned None - falling back to deterministic")
    
    # Fallback to deterministic generation
    logger.info("Using fallback deterministic draft generation")
    sections = generate_draft_fallback(rfp)
    
    logger.info(f"Deterministic draft completed: {len(sections)} sections")
    
    return DraftResponse(
        sections=sections,
        citations=citations,  # Include any citations found even for fallback
        generation_method="deterministic",
        kb_context_used=kb_context_used
    )

@router.post("/upload")
async def upload_rfp_file(file: UploadFile = File(...)):
    """Upload and extract text from RFP file (PDF, DOCX, TXT)"""
    
    # Validate file format
    if not file_service.is_supported_format(file.filename or ""):
        supported_formats = ", ".join(file_service.supported_formats)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported formats: {supported_formats}"
        )
    
    # Check file size (10MB limit)
    file_size = 0
    file_content = bytearray()
    
    try:
        # Read file content in chunks to check size
        async for chunk in file.stream():
            file_size += len(chunk)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(
                    status_code=413,
                    detail="File too large. Maximum size is 10MB."
                )
            file_content.extend(chunk)
        
        # Extract text from file
        extracted_text = file_service.extract_text(bytes(file_content), file.filename or "")
        
        if extracted_text is None:
            raise HTTPException(
                status_code=422,
                detail=f"Failed to extract text from {file.filename}. The file may be corrupted or in an unsupported format."
            )
        
        if not extracted_text.strip():
            raise HTTPException(
                status_code=422,
                detail=f"No text content found in {file.filename}. Please check that the file contains readable text."
            )
        
        logger.info(f"Successfully extracted {len(extracted_text)} characters from {file.filename}")
        
        return {
            "success": True,
            "filename": file.filename,
            "text": extracted_text,
            "char_count": len(extracted_text),
            "word_count": len(extracted_text.split())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload failed for {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )