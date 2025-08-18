# City Opportunity Backend

FastAPI + Pydantic backend for RFP analysis and draft generation with LLM integration.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Optional: Configure OpenAI API for enhanced analysis
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Features

- **LLM-Powered RFP Analysis**: Intelligently parse messy RFPs into structured requirements
- **AI Draft Generation**: Create professional, context-aware response drafts
- **Automatic Fallback**: Uses regex parsing + template generation if LLM unavailable
- **Enhanced Requirements**: Supports thresholds, confidence scores, source traceability
- **Flexible Configuration**: Works with or without OpenAI API key

## API Endpoints

### Analyze RFP
```bash
curl -X POST "http://localhost:8000/rfi/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "rfp_text": "We need a software solution with $250k budget...",
    "features": {
      "budget": "$250,000",
      "timeline": "6 months",
      "location": "Columbus, OH"
    }
  }'
```

### Draft Response
```bash
curl -X POST "http://localhost:8000/rfi/draft" \
  -H "Content-Type: application/json" \
  -d '{
    "rfp_text": "We need a software solution...",
    "features": {
      "budget": "$250,000",
      "timeline": "6 months"
    },
    "city": "Columbus",
    "industry": "Technology"
  }'
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY` (optional) - For LLM-enhanced drafting

### Data Files
- `app/config/keymap.json` - Parsing patterns and requirements mapping
- `app/data/sample_rfp.txt` - Sample RFP for testing

## Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app with CORS
│   ├── schemas.py       # Pydantic models
│   ├── rfi.py          # RFI analysis and drafting routes
│   ├── config/
│   │   └── keymap.json # Parsing configuration
│   └── data/
│       └── sample_rfp.txt
├── requirements.txt
└── README.md
```

## Development

The backend uses deterministic regex-based parsing to extract requirements from RFP text. No database or complex infrastructure required.

### Adding New Patterns

Edit `app/config/keymap.json` to add new extraction patterns:

```json
{
  "patterns": {
    "new_pattern": "regex_pattern_here"
  },
  "requirements": {
    "new_category": {
      "keywords": ["keyword1", "keyword2"],
      "priority": "High"
    }
  }
}
```

## Testing

Test the endpoints with the provided curl commands or use the frontend application.