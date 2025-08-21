# Evaluation Instructions - Quick Testing Guide

**Live Application**: https://ai-engineering-capstone-1.onrender.com

**Note**: If the live application is unavailable, please refer to the screenshots in the repository documentation to see the application functionality.

## City Opportunity Scoring (Homepage)
Select an industry from the dropdown menu and compare different cities' economic development scores. You'll see cities ranked by their suitability for that industry with detailed scoring breakdowns.

## Knowledge Base
Click the "Statistics" tab and then "Load Demo Data" to populate the knowledge base with economic development documents. You should see document and chunk counts increase, showing the system has loaded sample data successfully.

## RAG Search
Enter a question about economic development (e.g., "What incentives are available for manufacturing?") and optionally filter by jurisdiction or industry. The system will return relevant document excerpts with citations from the knowledge base.

## RFP Analysis
Paste an RFP document or use "Sample RFP" to fill the text area, then click "Analyze Requirements". You'll see a structured table of requirements with status indicators showing how well the sample data meets each requirement.

## RFP Response Generation
After analyzing an RFP, click "Generate Response" to create a professional draft response. The system will generate sections like Executive Summary and Technical Approach using the knowledge base context and city data.

## File Upload (Knowledge Base)
Upload a PDF, DOCX, or TXT file using the upload interface in the Knowledge Base section. The system will process the document, extract metadata, and add it to the searchable knowledge base.

---

## Future Enhancements

The application has several areas identified for improvement:

**User Experience**: Streamline the user flow by implementing dynamic city data loading when users type in custom city names, rather than being limited to the pre-loaded dataset. Add user authentication with login/logout functionality to enable personalized experiences and saved preferences.

**Knowledge Base Integration**: Fix the agent integration that currently works locally but fails in the deployed environment, ensuring the AI agent can properly access and query the knowledge base for enhanced RFP analysis and response generation.

**Data & Analytics**: Implement real-time data fetching from economic development APIs to provide current information rather than static demo data, and add user analytics to track feature usage and improve the platform based on actual user behavior.

---

**Note**: For full functionality, ensure the backend services (OpenAI API, Milvus vector database) are properly configured with valid API keys.