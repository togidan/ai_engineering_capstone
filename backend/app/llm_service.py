import os
import json
import logging
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-5-mini"  # Cost-effective model for structured tasks
        
    def is_available(self) -> bool:
        """Check if LLM service is available (API key configured)"""
        return self.client is not None
    
    def _chunk_rfp_by_headers(self, rfp_text: str) -> List[Tuple[str, str]]:
        """
        Split RFP into chunks based on headers/sections.
        Returns list of (header, content) tuples.
        """
        # Common RFP header patterns
        patterns = [
            r'^(\d+\.?\s+[A-Z][^.\n]{5,80})\s*$',   # "1. Introduction" or "1 Introduction"
            r'^([A-Z]\.?\s+[A-Z][^.\n]{5,80})\s*$',  # "A. Site Information" or "A Site Information"
            r'^([IVX]+\.?\s+[A-Z][^.\n]{5,80})\s*$',  # Roman numerals
            r'^([A-Z][A-Z\s]{5,80})\s*$',  # All caps headers
            r'^(#{1,3}\s+.+)$',  # Markdown headers
        ]
        
        chunks = []
        current_header = "Document Start"
        current_content = ""
        
        lines = rfp_text.split('\n')
        
        for i, line in enumerate(lines):
            is_header = False
            matched_header = None
            
            # Check if line matches any header pattern
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    matched_header = match.group(1).strip()
                    is_header = True
                    break
            
            if is_header and matched_header:
                # Save previous chunk if it has content
                if current_content.strip():
                    chunks.append((current_header, current_content.strip()))
                
                # Start new chunk
                current_header = matched_header
                current_content = ""
            else:
                current_content += line + '\n'
        
        # Add final chunk
        if current_content.strip():
            chunks.append((current_header, current_content.strip()))
        
        # If no headers found, return entire text as one chunk
        if len(chunks) <= 1:
            chunks = [("Full Document", rfp_text)]
        
        logger.info(f"Split RFP into {len(chunks)} chunks: {[h for h, _ in chunks]}")
        return chunks
    
    def parse_rfp(self, rfp_text: str, features: Dict[str, Any], user_action: str = "analyze", kb_context: str = "") -> Optional[Dict[str, Any]]:
        """
        Parse RFP using LLM with chunking and retry logic.
        Returns parsed JSON or None if LLM unavailable/failed
        """
        if not self.is_available():
            logger.warning("LLM service not available - no API key configured")
            return None
        
        # Check if RFP is large enough to benefit from chunking
        if len(rfp_text) > 8000:  # Threshold for chunking
            logger.info(f"Large RFP detected ({len(rfp_text)} chars), using chunked processing")
            return self._parse_rfp_chunked(rfp_text, features, user_action, kb_context)
        else:
            logger.info(f"Processing RFP as single chunk ({len(rfp_text)} chars)")
            return self._parse_rfp_single(rfp_text, features, user_action, kb_context)
    
    def _parse_rfp_single(self, rfp_text: str, features: Dict[str, Any], user_action: str = "analyze", kb_context: str = "") -> Optional[Dict[str, Any]]:
        """Parse RFP as single chunk with retry logic"""
        for attempt in range(2):  # 1 retry = 2 total attempts
            try:
                prompt = self._build_prompt(rfp_text, features, user_action, kb_context)
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an assistant that helps economic development teams respond to RFPs. You must return ONLY valid JSON according to the specified schema. Use provided knowledge base context to inform your responses and cite sources when relevant."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}  # Ensure JSON response
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.info(f"LLM parsing successful on attempt {attempt + 1}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Attempt {attempt + 1}: LLM returned invalid JSON: {e}")
                if attempt == 0:  # Only retry once
                    time.sleep(1)  # Brief delay before retry
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: LLM parsing failed: {e}")
                if attempt == 0:  # Only retry once
                    time.sleep(1)  # Brief delay before retry
        
        logger.error("All LLM parsing attempts failed")
        return None
    
    def _parse_rfp_chunked(self, rfp_text: str, features: Dict[str, Any], user_action: str = "analyze", kb_context: str = "") -> Optional[Dict[str, Any]]:
        """Parse RFP in chunks and combine results"""
        chunks = self._chunk_rfp_by_headers(rfp_text)
        
        all_requirements = []
        req_id_counter = 1
        data_sources_used = set()
        critical_gaps = []
        
        # Process each chunk
        for i, (header, content) in enumerate(chunks):
            chunk_result = self._parse_chunk(header, content, features, user_action, req_id_counter, kb_context)
            
            if chunk_result:
                chunk_requirements = chunk_result.get("requirements_table", [])
                all_requirements.extend(chunk_requirements)
                req_id_counter += len(chunk_requirements)
                
                # Accumulate summary data
                chunk_summary = chunk_result.get("summary", {})
                data_sources_used.update(chunk_summary.get("data_sources_used", []))
                critical_gaps.extend(chunk_summary.get("critical_gaps", []))
                
                logger.info(f"Processed chunk '{header}': {len(chunk_requirements)} requirements")
            else:
                logger.warning(f"Failed to process chunk '{header}'")
        
        if not all_requirements:
            logger.error("No chunks processed successfully")
            return None
        
        # Build combined response
        met_count = len([r for r in all_requirements if r.get("status") == "Met"])
        not_met_count = len([r for r in all_requirements if r.get("status") == "Not Met"])  
        unknown_count = len([r for r in all_requirements if r.get("status") == "Unknown"])
        
        combined_result = {
            "requirements_table": all_requirements,
            "summary": {
                "met": met_count,
                "not_met": not_met_count,
                "unknown": unknown_count,
                "critical_gaps": critical_gaps[:10],  # Limit to avoid overwhelming
                "data_sources_used": list(data_sources_used)
            }
        }
        
        # Add draft if requested
        if user_action == "draft" and all_requirements:
            combined_result["draft"] = self._generate_draft_from_requirements(all_requirements, features)
        
        logger.info(f"Successfully combined {len(chunks)} chunks into {len(all_requirements)} total requirements")
        return combined_result
    
    def _parse_chunk(self, header: str, content: str, features: Dict[str, Any], user_action: str, req_id_start: int, kb_context: str = "") -> Optional[Dict[str, Any]]:
        """Parse a single chunk with context about the overall document"""
        chunk_prompt = self._build_chunk_prompt(header, content, features, user_action, req_id_start, kb_context)
        
        for attempt in range(2):  # 1 retry = 2 total attempts
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": f"You are processing section '{header}' of an RFP. Extract requirements from this section only. Return valid JSON."},
                        {"role": "user", "content": chunk_prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                logger.debug(f"Successfully parsed chunk '{header}' on attempt {attempt + 1}")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Chunk '{header}' attempt {attempt + 1}: Invalid JSON: {e}")
                if attempt == 0:
                    time.sleep(0.5)  # Brief delay before retry
            except Exception as e:
                logger.error(f"Chunk '{header}' attempt {attempt + 1}: Failed: {e}")
                if attempt == 0:
                    time.sleep(0.5)  # Brief delay before retry
        
        logger.error(f"Failed to parse chunk '{header}' after all attempts")
        return None
    
    def _generate_draft_from_requirements(self, requirements: List[Dict], features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a basic draft structure from processed requirements"""
        # Group requirements by section
        sections_data = {}
        for req in requirements:
            section = req.get("section", "General")
            if section not in sections_data:
                sections_data[section] = []
            sections_data[section].append(req)
        
        sections = []
        appendix_metrics = []
        
        for section_name, section_reqs in sections_data.items():
            met_reqs = [r for r in section_reqs if r.get("status") == "Met"]
            content_parts = []
            
            if met_reqs:
                content_parts.append(f"We can address {len(met_reqs)} requirements in this section:")
                for req in met_reqs[:3]:  # Limit to avoid overwhelming
                    if req.get("answer_value"):
                        content_parts.append(f"- {req.get('requirement_text', '')}: {req.get('answer_value', '')}")
                        
                        # Add to appendix if numeric
                        if req.get("unit") and req.get("answer_value"):
                            appendix_metrics.append({
                                "metric": req.get("normalized_key", "").replace("_", " ").title(),
                                "value": f"{req.get('answer_value', '')} {req.get('unit', '')}".strip(),
                                "source": req.get("source_field", "")
                            })
            else:
                content_parts.append("Additional information needed for this section.")
            
            sections.append({
                "heading": section_name,
                "content": "\n".join(content_parts)
            })
        
        return {
            "enabled": True,
            "rfi_title": "Economic Development Response",
            "sections": sections,
            "appendix_metrics": appendix_metrics[:10]  # Limit metrics
        }
    
    def _build_chunk_prompt(self, header: str, content: str, features: Dict[str, Any], user_action: str, req_id_start: int, kb_context: str = "") -> str:
        """Build a focused prompt for processing a single chunk"""
        data_payload = {
            "features": features,
            "attachments": []
        }
        
        prompt = f"""You are processing the "{header}" section of an RFP document.

Extract requirements from this section ONLY. Do not invent requirements from other sections.

HARD RULES:
- Only extract requirements explicitly stated in this section
- Use ONLY the provided data fields to answer requirements
- Start requirement IDs from REQ-{req_id_start:03d}
- Return valid JSON following the schema exactly

OUTPUT JSON SCHEMA:
{{
  "requirements_table": [
    {{
      "id": "REQ-{req_id_start:03d}",
      "section": "{header}",
      "priority": "high" | "medium" | "low",
      "requirement_text": "verbatim from section",
      "normalized_key": "snake_case_key_or_null",
      "datatype": "number" | "text" | "boolean" | "date" | "file",
      "unit": "string_or_null",
      "logic": {{
        "threshold_min": "number_or_null",
        "threshold_max": "number_or_null",
        "options": ["optional list"],
        "format": "optional string"
      }},
      "answer_value": "string_or_null",
      "status": "Met" | "Not Met" | "Unknown",
      "source_field": "features.field_name_or_null",
      "source_attachment": null,
      "confidence": 0.0,
      "notes": "short rationale or TODO"
    }}
  ],
  "summary": {{
    "met": 0,
    "not_met": 0,
    "unknown": 0,
    "critical_gaps": ["high-priority missing items"],
    "data_sources_used": ["features.field_name"]
  }}
}}

SECTION CONTENT:
{content}

AVAILABLE DATA FIELDS:
Location & Infrastructure: city, state, cbsa, population, major_highway_access, rail_access, airport_distance_miles
Sites & Utilities: available_industrial_acres, industrial_power_cents_kwh, broadband_100_20_pct, permitting_days_major
Workforce & Education: stem_share_pct, manufacturing_emp_share_pct, university_research_usd_m, workforce_training_programs
Economic Indicators: median_income_usd, median_rent_usd, logistics_index
Incentives: tax_increment_financing, enterprise_zone_benefits, property_tax_abatement, job_creation_tax_credit, research_development_credit

DATA PAYLOAD:
{json.dumps(data_payload, indent=2)}

KNOWLEDGE BASE CONTEXT (if available):
{kb_context if kb_context else "No additional context available from knowledge base."}

KB INTEGRATION NOTES:
- Use KB context to inform requirement status assessments
- Reference available data sources from both features AND KB content
- Note relevant KB documents in requirement notes when applicable

Return the JSON response now:"""
        
        return prompt
    
    def _build_prompt(self, rfp_text: str, features: Dict[str, Any], user_action: str, kb_context: str = "") -> str:
        """Build the structured prompt with RFP text and available data"""
        
        data_payload = {
            "features": features,
            "attachments": []  # Empty for now, can be extended later
        }
        
        prompt = f"""You are an assistant that helps economic development teams respond to RFPs.

Your job, in order:
1) Parse the provided RFP text and extract a clean, deduplicated TABLE of requirements.
2) Map each requirement to the available data payload (ONLY what is provided), answer what you can, and mark the rest with TODOs.
3) Return a JSON object with both (a) the requirements_table and (b) if requested, a draft RFP response built strictly from those answers.

HARD RULES
- Grounding: Do NOT invent facts. Use ONLY the fields/content provided in `data` and `attachments`. If unknown, write a concise TODO.
- Traceability: For every answered requirement, include `source_field` (e.g., "features.stem_share_pct") or `source_attachment`.
- Determinism: Normalize numbers with units (%, $m, ¢/kWh, acres, MGD). Keep language concise.
- Structure: Follow the output JSON schema EXACTLY. No extra keys. No prose outside JSON.
- RFP Draft: Only generate if `user_action` == "draft". Otherwise, just produce the table.

REQUIREMENT NORMALIZATION (how to interpret RFP lines)
- Capture: requirement_text (as written), section (e.g., "Workforce", "Sites"), priority (high if explicit "must/shall"), datatype (number | text | boolean | date | file), unit (if numeric), and logic:
  - threshold_min / threshold_max (for numeric), options (for categorical), format (for file/spec).
- Typical categories: Location & Infrastructure, Workforce & Education, Incentives, Sites & Utilities, Regulatory/Permitting, Timeline/Process, Submission Format.
- Examples of mapping:
  - "Provide % of STEM workforce" → datatype:number, unit:%, normalized_key:"stem_share_pct"
  - "Industrial power cost (¢/kWh)" → number, unit:¢/kWh, normalized_key:"industrial_power_cents_kwh"
  - "Parcel size ≥ 150 acres" → number, unit:acres, threshold_min:150, normalized_key:"available_industrial_acres"
  - "Permitting within 120 days" → number, unit:days, threshold_max:120, normalized_key:"permitting_days_major"
  - "Attach site map PDF" → datatype:file, format:pdf, normalized_key:"site_map_pdf"

ANSWERING LOGIC
- For each requirement, try to resolve from `data.features` first, then `data.attachments` text.
- Populate: answer_value (string with units), status ("Met" | "Not Met" | "Unknown"), source_field/source_attachment, confidence (0–1), notes (short rationale or TODO).
- If partially satisfied (e.g., 120-day permit vs. ≤90 requested), status = "Not Met" and notes explain gap.
- If the RFP requests a document and none provided, status = "Unknown" with TODO.

OUTPUT JSON SCHEMA (return ONLY this JSON)
{{
  "requirements_table": [
    {{
      "id": "REQ-001",
      "section": "Sites & Utilities",
      "priority": "high" | "medium" | "low",
      "requirement_text": "verbatim from RFP",
      "normalized_key": "snake_case_key_or_null",
      "datatype": "number" | "text" | "boolean" | "date" | "file",
      "unit": "string_or_null",
      "logic": {{
        "threshold_min": "number_or_null",
        "threshold_max": "number_or_null",
        "options": ["optional list"],
        "format": "optional string"
      }},
      "answer_value": "string_or_null",
      "status": "Met" | "Not Met" | "Unknown",
      "source_field": "features.foo_bar_or_null",
      "source_attachment": "Attachment Name or null",
      "confidence": 0.0,
      "notes": "short rationale or TODO"
    }}
  ],
  "summary": {{
    "met": 0,
    "not_met": 0,
    "unknown": 0,
    "critical_gaps": ["short bullets of high-priority TODOs"],
    "data_sources_used": ["features.stem_share_pct","attachments:Site A brief"]
  }},
  "draft": {{
    "enabled": true | false,
    "rfi_title": "string_or_null",
    "sections": [
      {{"heading":"Location & Infrastructure","content":"markdown"}},
      {{"heading":"Workforce & Education","content":"markdown"}},
      {{"heading":"Incentives & Programs","content":"markdown"}},
      {{"heading":"Sites & Utilities","content":"markdown"}},
      {{"heading":"Regulatory & Permitting","content":"markdown"}},
      {{"heading":"Timeline & Submission","content":"markdown"}}
    ],
    "appendix_metrics": [
      {{"metric":"STEM share","value":"16.5%","source":"features.stem_share_pct"}},
      {{"metric":"Industrial power price","value":"8.1 ¢/kWh","source":"features.industrial_power_cents_kwh"}}
    ]
  }}
}}

DRAFTING RULES (only if user_action == "draft")
- Use only requirements_table answers with status != "Unknown".
- If a section lacks data, include concise TODO bullets at the end of that section.
- Keep each section ≤ 180 words. Professional, specific tone. No marketing fluff.
- Add inline metric tables sparingly (one per section max), derived from answers.

RFP TEXT:
{rfp_text}

AVAILABLE DATA FIELDS (use these exact field names in source_field):
Location & Infrastructure:
- city: City name
- state: State abbreviation  
- cbsa: Core Based Statistical Area code
- population: Metropolitan area population
- major_highway_access: Major highways serving the area
- rail_access: Rail service providers
- airport_distance_miles: Distance to major airport

Sites & Utilities:
- available_industrial_acres: Industrial land available for development
- industrial_power_cents_kwh: Industrial electricity rate in cents per kWh
- broadband_100_20_pct: Percentage with 100/20 Mbps broadband access
- permitting_days_major: Days for major project permitting

Workforce & Education:
- stem_share_pct: Percentage of workforce in STEM occupations
- manufacturing_emp_share_pct: Manufacturing employment share percentage
- university_research_usd_m: Annual university research spending in millions USD
- workforce_training_programs: Available workforce development programs

Economic Indicators:
- median_income_usd: Metropolitan area median household income
- median_rent_usd: Median residential rent
- logistics_index: Transportation/logistics connectivity score (0-1)

Incentives & Programs:
- tax_increment_financing: TIF availability status
- enterprise_zone_benefits: Enterprise zone benefits available
- property_tax_abatement: Property tax abatement terms
- job_creation_tax_credit: Job creation tax credit amount
- research_development_credit: R&D tax credit percentage

DATA PAYLOAD:
{json.dumps(data_payload, indent=2)}

USER_ACTION: {user_action}

KNOWLEDGE BASE CONTEXT (if available):
{kb_context if kb_context else "No additional context available from knowledge base."}

KNOWLEDGE BASE INTEGRATION FOR ANALYSIS:
- Use KB context to inform requirement status assessments
- Reference available data sources when determining if requirements can be met
- If KB contains relevant documents, note them in requirement notes
- For data availability assessment, consider both features AND KB content
- Mark requirements as "Met" if either features OR KB sources can satisfy them
- Use KB context to suggest data collection strategies in notes
- Reference KB document titles when available data sources are found

CITATION REQUIREMENTS:
- Reference KB sources in requirement notes when relevant
- Format: "See [Document Title] for additional context"
- Mention specific data availability from KB documents
- Note gaps where additional KB content would be helpful

Return the JSON response now:"""

        return prompt

# Global LLM service instance
llm_service = LLMService()