"""
Quality Service - Data quality checks and validation for the knowledge base
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class QualityService:
    def __init__(self):
        self.min_text_length = 500
        self.min_chunks = 3
        self.max_z_score = 4.0
        
        # Historical bounds for economic data validation
        self.economic_bounds = {
            "stem_share_pct": (5.0, 35.0),           # 5-35% STEM workforce
            "manufacturing_emp_share_pct": (3.0, 25.0), # 3-25% manufacturing
            "industrial_power_cents_kwh": (4.0, 15.0),  # 4-15 cents/kWh
            "median_income_usd": (25000, 150000),       # $25K-150K median income
            "unemployment_rate": (1.0, 15.0),           # 1-15% unemployment
            "population": (10000, 10000000),             # 10K-10M population
            "university_research_usd_m": (0, 5000),     # $0-5B research spending
            "broadband_coverage_pct": (60.0, 100.0),    # 60-100% broadband
            "permitting_days": (15, 365),               # 15-365 days permitting
            "logistics_index": (0.0, 1.0)               # 0-1 logistics score
        }
        
    def validate_document_quality(self, text: str, chunks: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive document quality validation
        Returns quality assessment with pass/fail status and recommendations
        """
        
        quality_report = {
            "passed": True,
            "score": 100,
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "metrics": {
                "text_length": len(text),
                "chunk_count": len(chunks),
                "avg_chunk_length": np.mean([len(chunk) for chunk in chunks]) if chunks else 0,
                "metadata_completeness": 0
            }
        }
        
        # 1. Text length validation
        if len(text) < self.min_text_length:
            quality_report["passed"] = False
            quality_report["score"] -= 30
            quality_report["issues"].append(f"Text too short: {len(text)} chars (minimum: {self.min_text_length})")
            quality_report["recommendations"].append("Provide more comprehensive document content")
        
        # 2. Chunk generation validation
        if len(chunks) < self.min_chunks:
            quality_report["passed"] = False
            quality_report["score"] -= 25
            quality_report["issues"].append(f"Insufficient chunks: {len(chunks)} (minimum: {self.min_chunks})")
            quality_report["recommendations"].append("Document may be too short or lack structure for effective chunking")
        
        # 3. Chunk quality validation
        if chunks:
            chunk_lengths = [len(chunk) for chunk in chunks]
            avg_length = np.mean(chunk_lengths)
            min_length = min(chunk_lengths)
            
            if min_length < 100:
                quality_report["warnings"].append("Some chunks are very short (<100 chars)")
                quality_report["score"] -= 5
            
            if avg_length < 300:
                quality_report["warnings"].append("Average chunk length is low, may affect search quality")
                quality_report["score"] -= 10
        
        # 4. Metadata completeness validation
        required_fields = ["title", "jurisdiction", "industry", "doc_type"]
        optional_fields = ["source_url", "keywords", "summary"]
        
        completeness_score = 0
        for field in required_fields:
            if metadata.get(field):
                completeness_score += 20
            else:
                quality_report["warnings"].append(f"Missing required metadata: {field}")
                quality_report["score"] -= 10
        
        for field in optional_fields:
            if metadata.get(field):
                completeness_score += 5
        
        quality_report["metrics"]["metadata_completeness"] = min(completeness_score, 100)
        
        # 5. Content relevance validation
        text_lower = text.lower()
        econ_dev_terms = [
            "economic", "development", "business", "industry", "manufacturing",
            "incentive", "tax", "workforce", "infrastructure", "investment",
            "jobs", "employment", "city", "region", "municipality"
        ]
        
        term_matches = sum(1 for term in econ_dev_terms if term in text_lower)
        if term_matches < 3:
            quality_report["warnings"].append("Document may not be relevant to economic development")
            quality_report["score"] -= 15
        
        # 6. Historical date validation
        current_year = datetime.now().year
        old_dates = re.findall(r'\b(19\d{2}|200[0-9])\b', text)
        if old_dates:
            oldest_year = min(int(year) for year in old_dates)
            if oldest_year < current_year - 20:
                quality_report["warnings"].append(f"Document contains very old dates (oldest: {oldest_year})")
                quality_report["recommendations"].append("Consider marking as historical or updating content")
        
        return quality_report
    
    def validate_economic_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate economic data for range checks and outlier detection
        """
        
        validation_report = {
            "passed": True,
            "issues": [],
            "warnings": [],
            "outliers": [],
            "metrics": {
                "fields_validated": 0,
                "fields_passed": 0,
                "outlier_count": 0
            }
        }
        
        for field, value in data.items():
            if field in self.economic_bounds:
                validation_report["metrics"]["fields_validated"] += 1
                
                try:
                    # Convert to numeric if string
                    if isinstance(value, str):
                        # Remove common formatting
                        clean_value = re.sub(r'[^\d.-]', '', value.replace(',', ''))
                        if clean_value:
                            numeric_value = float(clean_value)
                        else:
                            continue
                    else:
                        numeric_value = float(value)
                    
                    # Range validation
                    min_val, max_val = self.economic_bounds[field]
                    
                    if numeric_value < min_val or numeric_value > max_val:
                        validation_report["issues"].append(
                            f"{field}: {numeric_value} outside valid range [{min_val}, {max_val}]"
                        )
                        validation_report["passed"] = False
                    else:
                        validation_report["metrics"]["fields_passed"] += 1
                    
                    # Z-score outlier detection (simplified)
                    # Using midpoint as mean for basic outlier detection
                    midpoint = (min_val + max_val) / 2
                    range_size = max_val - min_val
                    z_score = abs(numeric_value - midpoint) / (range_size / 4)
                    
                    if z_score > self.max_z_score:
                        validation_report["outliers"].append({
                            "field": field,
                            "value": numeric_value,
                            "z_score": round(z_score, 2)
                        })
                        validation_report["metrics"]["outlier_count"] += 1
                        validation_report["warnings"].append(
                            f"{field}: {numeric_value} is a statistical outlier (z-score: {z_score:.2f})"
                        )
                
                except (ValueError, TypeError):
                    validation_report["warnings"].append(f"{field}: Could not validate '{value}' as numeric")
        
        return validation_report
    
    def check_knowledge_base_staleness(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check for stale or outdated content in the knowledge base
        """
        
        staleness_report = {
            "total_documents": len(documents),
            "stale_documents": 0,
            "historical_documents": 0,
            "recent_documents": 0,
            "issues": [],
            "recommendations": []
        }
        
        current_year = datetime.now().year
        cutoff_year = current_year - 5  # Content older than 5 years considered stale
        
        for doc in documents:
            doc_age_indicators = []
            
            # Check creation date
            if doc.get("created_at"):
                try:
                    created_date = datetime.fromisoformat(doc["created_at"].replace('Z', '+00:00'))
                    if created_date.year < cutoff_year:
                        doc_age_indicators.append("old_creation_date")
                except:
                    pass
            
            # Check content for date references
            content_text = doc.get("summary", "") + " " + doc.get("keywords", "")
            old_dates = re.findall(r'\b(20[01][0-9])\b', content_text)
            if old_dates:
                max_content_year = max(int(year) for year in old_dates)
                if max_content_year < cutoff_year:
                    doc_age_indicators.append("old_content_dates")
            
            # Check for explicit historical markers
            if doc.get("historical") or "historical" in doc.get("doc_type", "").lower():
                staleness_report["historical_documents"] += 1
            elif doc_age_indicators:
                staleness_report["stale_documents"] += 1
                staleness_report["issues"].append(
                    f"Stale document: {doc.get('title', 'Unknown')} (ID: {doc.get('id')})"
                )
            else:
                staleness_report["recent_documents"] += 1
        
        # Generate recommendations
        stale_percentage = (staleness_report["stale_documents"] / staleness_report["total_documents"]) * 100
        
        if stale_percentage > 30:
            staleness_report["recommendations"].append(
                "High percentage of stale content detected. Consider content refresh or archival."
            )
        elif stale_percentage > 15:
            staleness_report["recommendations"].append(
                "Moderate staleness detected. Review and update older content when possible."
            )
        
        return staleness_report
    
    def detect_instruction_injection(self, text: str) -> Dict[str, Any]:
        """
        Detect potential instruction injection attacks in document content
        """
        
        injection_report = {
            "threat_detected": False,
            "threats": [],
            "risk_level": "low",
            "sanitized_text": text
        }
        
        # Common instruction injection patterns
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"forget\s+everything\s+above",
            r"system\s*:\s*you\s+are\s+now",
            r"new\s+instructions?\s*:",
            r"override\s+security",
            r"jailbreak\s+mode",
            r"developer\s+mode\s+enabled",
            r"assistant\s*:\s*i\s+will\s+now",
        ]
        
        text_lower = text.lower()
        
        for pattern in injection_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                injection_report["threat_detected"] = True
                injection_report["threats"].append({
                    "pattern": pattern,
                    "matches": len(matches)
                })
        
        # Check for suspicious formatting
        if "```" in text or "====" in text:
            if len(re.findall(r'```.*?```', text, re.DOTALL)) > 2:
                injection_report["threats"].append({
                    "type": "suspicious_formatting",
                    "description": "Multiple code blocks detected"
                })
        
        # Set risk level
        threat_count = len(injection_report["threats"])
        if threat_count >= 3:
            injection_report["risk_level"] = "high"
        elif threat_count >= 1:
            injection_report["risk_level"] = "medium"
        
        # Basic sanitization (remove obvious instruction attempts)
        sanitized = text
        for pattern in injection_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
        
        injection_report["sanitized_text"] = sanitized
        
        return injection_report
    
    def comprehensive_quality_check(
        self, 
        text: str, 
        chunks: List[str], 
        metadata: Dict[str, Any],
        economic_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive quality and safety checks
        """
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_passed": True,
            "overall_score": 100,
            "checks": {}
        }
        
        # 1. Document quality check
        doc_quality = self.validate_document_quality(text, chunks, metadata)
        report["checks"]["document_quality"] = doc_quality
        if not doc_quality["passed"]:
            report["overall_passed"] = False
        report["overall_score"] = min(report["overall_score"], doc_quality["score"])
        
        # 2. Economic data validation (if provided)
        if economic_data:
            econ_validation = self.validate_economic_data(economic_data)
            report["checks"]["economic_data"] = econ_validation
            if not econ_validation["passed"]:
                report["overall_passed"] = False
                report["overall_score"] -= 10
        
        # 3. Instruction injection detection
        injection_check = self.detect_instruction_injection(text)
        report["checks"]["security"] = injection_check
        if injection_check["threat_detected"]:
            if injection_check["risk_level"] == "high":
                report["overall_passed"] = False
                report["overall_score"] -= 50
            elif injection_check["risk_level"] == "medium":
                report["overall_score"] -= 20
        
        # 4. Content sanitization
        report["sanitized_content"] = {
            "text": injection_check["sanitized_text"],
            "sanitization_applied": injection_check["threat_detected"]
        }
        
        return report

# Global quality service instance
quality_service = QualityService()