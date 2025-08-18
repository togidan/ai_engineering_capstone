# Knowledge Base Bootstrap Instructions

This guide explains how to populate your knowledge base with Wikipedia data for economic development analysis.

## Prerequisites

1. **Backend server running**:
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Dependencies installed**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment configured**:
   - OpenAI API key in `.env` file (for embeddings)
   - Milvus service available (Docker or local)

## Running the Bootstrap

### Option 1: Quick Bootstrap (Recommended)
```bash
cd backend/scripts
python wiki_bootstrap.py
```

This will:
- ✅ Fetch Wikipedia data for 25+ major US cities
- ✅ Filter content for economic development topics
- ✅ Upload via the KB API (includes LLM metadata generation)
- ✅ Chunk text and create embeddings automatically
- ✅ Target: 500-1000+ searchable chunks

### Option 2: Original Script (More Advanced)
```bash
cd backend/scripts
python ingest_wiki.py
```

## What Gets Ingested

**Cities covered:**
- Columbus, Cleveland, Cincinnati (Ohio)
- Austin, Dallas, Houston (Texas) 
- Denver, Colorado Springs (Colorado)
- Atlanta, Nashville, Seattle, Portland
- Phoenix, Tucson, Charlotte, Raleigh
- Indianapolis, Detroit, Milwaukee
- Kansas City, Oklahoma City, Las Vegas
- And more...

**Content focus:**
- Economic profiles and statistics
- Industry presence and manufacturing
- Transportation and infrastructure
- Workforce and education data
- Demographics and business climate
- University research capabilities

## Expected Results

**Successful run should produce:**
- 📄 25+ documents in the knowledge base
- 🔍 500-1000+ searchable text chunks
- 🎯 Vector embeddings for semantic search
- 📊 Metadata including city names and economic topics

## Verification

1. **Check KB stats:**
   ```bash
   curl http://localhost:8000/kb/stats
   ```

2. **Test search:**
   ```bash
   curl -X POST http://localhost:8000/kb/search \
     -H "Content-Type: application/json" \
     -d '{"query": "manufacturing workforce Columbus"}'
   ```

3. **Frontend verification:**
   - Open the Knowledge Base tab
   - View statistics showing documents and chunks
   - Try searching for cities or economic topics

## Troubleshooting

**API Connection Issues:**
- Ensure backend server is running on port 8000
- Check firewall/network connectivity

**Wikipedia Fetch Errors:**
- Some cities may fail due to disambiguation
- This is normal - script will continue with other cities

**OpenAI/Embedding Issues:**
- Check `.env` file has valid `OPENAI_API_KEY`
- Documents will still be stored without embeddings

**Milvus Issues:**
- Vector search won't work without Milvus
- Documents are still stored in SQLite database

## Performance Notes

- **Runtime:** 10-20 minutes for full bootstrap
- **Rate limiting:** 2-second delays between cities
- **Memory usage:** Moderate (handles one city at a time)
- **Storage:** ~50-100MB for full dataset

The bootstrap creates a solid foundation for testing RFP analysis with real economic development data!