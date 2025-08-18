"""
LLM Metadata Service - Generate document metadata using OpenAI
"""

import os
import json
import logging
from typing import Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMMetadataService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-4o-mini"  # Fast, cost-effective model for metadata tasks
        
    def is_available(self) -> bool:
        """Check if LLM service is available (API key configured)"""
        return self.client is not None
    
    def generate_metadata(self, text: str, filename: str) -> Dict[str, Any]:
        """
        Generate document metadata using LLM.
        
        Args:
            text: Extracted text content from the document
            filename: Original filename
            
        Returns:
            Dict with keys: name, description
            
        Raises:
            Exception: If LLM service unavailable or generation fails
        """
        
        if not self.is_available():
            raise Exception("LLM service unavailable - OpenAI API key not configured")
        
        # Truncate text if too long (keep first 4000 chars for context)
        text_sample = text[:4000] if len(text) > 4000 else text
        
        try:
            prompt = self._build_metadata_prompt(text_sample, filename)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a document analysis assistant. Generate concise, accurate metadata for documents. Return only valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for consistent metadata
                max_tokens=300    # Concise responses
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate required fields
            required_fields = ["name", "description"]
            for field in required_fields:
                if field not in result:
                    raise Exception(f"LLM response missing required field: {field}")
            
            # Limit description length
            if len(result["description"]) > 500:
                result["description"] = result["description"][:497] + "..."
            
            logger.info(f"Generated metadata for {filename}: {result['name']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON for {filename}: {e}")
            raise Exception("Failed to generate metadata - invalid LLM response format")
            
        except Exception as e:
            logger.error(f"LLM metadata generation failed for {filename}: {e}")
            raise Exception(f"Failed to generate metadata: {str(e)}")
    
    def _build_metadata_prompt(self, text: str, filename: str) -> str:
        """Build the metadata generation prompt"""
        
        prompt = f"""Analyze this document and generate metadata.

DOCUMENT INFO:
- Filename: {filename}
- Content preview: {text}

TASK:
Generate concise metadata for this document. Focus on what the document actually contains.

OUTPUT JSON SCHEMA:
{{
  "name": "Clear, descriptive name for the document (30-80 characters)",
  "description": "2-3 sentence summary of document content and purpose (100-300 characters)"
}}

GUIDELINES:
- name: Should be professional and descriptive, not just the filename
- description: Focus on content, purpose, and key information
- Be factual and specific, avoid marketing language
- If document is about economic development, mention specific aspects
- If document contains data/metrics, mention that
- Keep descriptions concise but informative

Return only the JSON object:"""

        return prompt

# Global service instance
llm_metadata_service = LLMMetadataService()