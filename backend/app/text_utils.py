import re
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)

class TextProcessor:
    def __init__(self):
        # Economic development domain terms for validation
        self.econ_dev_terms = {
            "location": ["city", "state", "county", "region", "metro", "area", "location", "site", "facility"],
            "incentives": ["incentive", "tax", "credit", "abatement", "rebate", "grant", "funding", "financing"],
            "workforce": ["jobs", "employment", "workforce", "labor", "skill", "training", "education"],
            "industry": ["manufacturing", "biotech", "logistics", "cleantech", "aerospace", "software", "tech"],
            "infrastructure": ["transport", "airport", "rail", "highway", "broadband", "utility", "power"],
            "economic": ["economy", "economic", "development", "investment", "business", "company", "enterprise"],
            "research": ["university", "research", "innovation", "r&d", "stem"]
        }
        
        # Industry allowlist
        self.industries = {
            "advanced manufacturing", "manufacturing", "biotech", "biotechnology",
            "logistics", "cleantech", "aerospace", "software", "technology",
            "healthcare", "agriculture", "energy", "automotive", "finance"
        }
        
        # Document type categories
        self.doc_types = {
            "case_study", "incentive", "policy", "city_profile", 
            "rfp_example", "press_release", "economic_data", "other"
        }
        
        # Common stopwords
        self.stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "before", "after", "above", "below", "is", "are", "was", "were", "been",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "can", "this", "that", "these", "those"
        }
    
    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 80) -> List[str]:
        """
        Chunk text into overlapping segments of approximately chunk_size tokens.
        Uses simple word-based approximation (1 token ≈ 0.75 words).
        """
        if not text or len(text.strip()) < 100:
            return []
        
        # Clean text
        text = self._clean_text(text)
        words = text.split()
        
        if len(words) < 50:  # Too short to chunk meaningfully
            return [text] if len(text) >= 500 else []
        
        # Convert token sizes to word estimates
        words_per_chunk = int(chunk_size * 0.75)  # ~800 tokens ≈ 600 words
        words_overlap = int(overlap * 0.75)       # ~80 tokens ≈ 60 words
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = start + words_per_chunk
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            
            # Only include chunks with sufficient content
            if len(chunk_text) >= 500:
                chunks.append(chunk_text)
            
            # Move start position with overlap
            start = end - words_overlap
            
            # Break if we're not making progress
            if end >= len(words):
                break
        
        # Ensure we get at least some chunks for reasonable-length documents
        if not chunks and len(text) >= 500:
            chunks = [text]
            
        logger.info(f"Generated {len(chunks)} chunks from {len(words)} words")
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\/\&\%\$\#\@]', ' ', text)
        
        # Remove repeated characters (like ---- or ....)
        text = re.sub(r'(.)\1{3,}', r'\1\1', text)
        
        return text
    
    def extract_metadata(self, text: str, filename: str = "") -> Dict[str, Any]:
        """
        Auto-extract metadata from text using heuristics.
        Returns extracted jurisdiction, industry, doc_type, keywords, and summary.
        """
        metadata = {
            "title": self._extract_title(text, filename),
            "jurisdiction": self._extract_jurisdiction(text),
            "industry": self._extract_industry(text),
            "doc_type": self._extract_doc_type(text, filename),
            "keywords": self._extract_keywords(text),
            "summary": self._extract_summary(text)
        }
        
        logger.info(f"Extracted metadata: {metadata}")
        return metadata
    
    def _extract_title(self, text: str, filename: str) -> str:
        """Extract or generate title"""
        # Try to find title in first few lines
        lines = text.split('\n')[:5]
        for line in lines:
            line = line.strip()
            if 20 <= len(line) <= 100 and not line.lower().startswith(('the ', 'this ', 'a ')):
                return line
        
        # Fall back to filename
        if filename:
            title = Path(filename).stem.replace('_', ' ').replace('-', ' ')
            return title.title()
        
        # Generate from first sentence
        sentences = re.split(r'[.!?]', text)
        if sentences and len(sentences[0]) <= 100:
            return sentences[0].strip()
        
        return "Untitled Document"
    
    def _extract_jurisdiction(self, text: str) -> Optional[str]:
        """Extract jurisdiction (city, state, region) from text"""
        # State patterns
        state_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),?\s+([A-Z]{2})\b'
        state_matches = re.findall(state_pattern, text)
        
        if state_matches:
            city, state = state_matches[0]
            return f"{city}, {state}"
        
        # Just state abbreviations
        state_abbrev_pattern = r'\b([A-Z]{2})\b'
        state_matches = re.findall(state_abbrev_pattern, text)
        common_states = {"CA", "NY", "TX", "FL", "OH", "PA", "IL", "MI", "NC", "GA"}
        
        for state in state_matches:
            if state in common_states:
                return state
        
        # Major cities
        major_cities = {
            "new york", "los angeles", "chicago", "houston", "phoenix", "philadelphia",
            "san antonio", "san diego", "dallas", "san jose", "austin", "columbus",
            "charlotte", "san francisco", "indianapolis", "seattle", "denver",
            "washington", "boston", "nashville", "detroit", "portland", "memphis",
            "baltimore", "milwaukee", "albuquerque", "atlanta", "colorado springs"
        }
        
        text_lower = text.lower()
        for city in major_cities:
            if city in text_lower:
                return city.title()
        
        return None
    
    def _extract_industry(self, text: str) -> Optional[str]:
        """Extract industry from text using allowlist matching"""
        text_lower = text.lower()
        
        # Score each industry by frequency of mentions
        industry_scores = {}
        for industry in self.industries:
            count = text_lower.count(industry.lower())
            if count > 0:
                industry_scores[industry] = count
        
        if industry_scores:
            # Return most mentioned industry
            return max(industry_scores, key=industry_scores.get)
        
        return None
    
    def _extract_doc_type(self, text: str, filename: str = "") -> str:
        """Categorize document type"""
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Check filename first
        if any(term in filename_lower for term in ["case", "study"]):
            return "case_study"
        if any(term in filename_lower for term in ["incentive", "tax", "credit"]):
            return "incentive"
        if any(term in filename_lower for term in ["policy", "ordinance", "regulation"]):
            return "policy"
        if any(term in filename_lower for term in ["profile", "overview", "about"]):
            return "city_profile"
        if any(term in filename_lower for term in ["rfp", "request", "proposal"]):
            return "rfp_example"
        if any(term in filename_lower for term in ["press", "news", "release"]):
            return "press_release"
        
        # Check content
        if "case study" in text_lower or "success story" in text_lower:
            return "case_study"
        if any(term in text_lower for term in ["tax incentive", "tax credit", "abatement"]):
            return "incentive"
        if any(term in text_lower for term in ["policy", "ordinance", "regulation", "zoning"]):
            return "policy"
        if "request for proposal" in text_lower or "rfp" in text_lower:
            return "rfp_example"
        if any(term in text_lower for term in ["press release", "announces", "announcement"]):
            return "press_release"
        if any(term in text_lower for term in ["economic data", "statistics", "census"]):
            return "economic_data"
        
        return "other"
    
    def _extract_keywords(self, text: str, max_keywords: int = 12) -> str:
        """Extract top keywords as comma-separated string"""
        # Simple frequency-based keyword extraction
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Remove stopwords
        words = [w for w in words if w not in self.stopwords]
        
        # Count frequencies
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in top_words[:max_keywords] if freq >= 2]
        
        return ", ".join(keywords[:max_keywords])
    
    def _extract_summary(self, text: str, max_sentences: int = 3) -> str:
        """Extract summary from first few sentences"""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter sentences
        good_sentences = []
        for sentence in sentences[:10]:  # Look at first 10 sentences
            sentence = sentence.strip()
            if 20 <= len(sentence) <= 200 and not sentence.lower().startswith(('table', 'figure', 'page')):
                good_sentences.append(sentence)
                if len(good_sentences) >= max_sentences:
                    break
        
        if good_sentences:
            return ". ".join(good_sentences) + "."
        
        # Fallback to first 200 characters
        return text[:200].strip() + "..." if len(text) > 200 else text.strip()
    
    def validate_domain_query(self, query: str) -> bool:
        """Check if query contains economic development terms"""
        query_lower = query.lower()
        
        # Check if query contains any economic development terms
        for category, terms in self.econ_dev_terms.items():
            if any(term in query_lower for term in terms):
                return True
        
        return False
    
    def calculate_keyword_overlap(self, query: str, text: str) -> float:
        """Calculate keyword overlap fraction between query and text"""
        query_words = set(re.findall(r'\b[a-z]{3,}\b', query.lower()))
        text_words = set(re.findall(r'\b[a-z]{3,}\b', text.lower()))
        
        # Remove stopwords
        query_words = query_words - self.stopwords
        text_words = text_words - self.stopwords
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words & text_words)
        return overlap / len(query_words)
    
    def validate_document_quality(self, text: str, chunks: List[str]) -> Dict[str, Any]:
        """Validate document meets quality thresholds"""
        return {
            "text_length_ok": len(text) >= 500,
            "chunk_count_ok": len(chunks) >= 3,
            "text_length": len(text),
            "chunk_count": len(chunks),
            "passed": len(text) >= 500 and len(chunks) >= 3
        }

# Global text processor instance
text_processor = TextProcessor()