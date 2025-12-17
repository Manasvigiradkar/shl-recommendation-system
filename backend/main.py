"""
SHL Assessment Recommendation System - FastAPI Backend
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions
import os
import json

# Initialize FastAPI
app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="AI-powered assessment recommendation system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")
genai.configure(api_key=GEMINI_API_KEY)

# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=GEMINI_API_KEY
)

# Get or create collection
try:
    collection = chroma_client.get_collection(
        name="shl_assessments",
        embedding_function=embedding_function
    )
except:
    collection = chroma_client.create_collection(
        name="shl_assessments",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )

# Pydantic models
class QueryRequest(BaseModel):
    query: str

class AssessmentRecommendation(BaseModel):
    assessment_name: str
    url: str
    score: Optional[float] = None

class RecommendResponse(BaseModel):
    query: str
    recommendations: List[AssessmentRecommendation]
    processing_time: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    message: str

# Helper functions
def query_llm_for_reranking(query: str, candidates: List[dict]) -> List[dict]:
    """Use Gemini to rerank and filter candidates based on relevance."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Create a prompt for the LLM
    prompt = f"""You are an expert HR assessment recommender. Given a job query and a list of assessment candidates, 
    you need to select the most relevant assessments and provide a balanced mix.

Query: {query}

Candidates:
{json.dumps([{"name": c["name"], "description": c.get("description", ""), "test_type": c.get("test_type", "")} for c in candidates[:20]], indent=2)}

Instructions:
1. Select 5-10 most relevant assessments
2. Balance between different test types (Knowledge & Skills, Personality & Behavior, etc.)
3. Prioritize assessments that directly match the job requirements
4. Return ONLY a JSON array of assessment names in order of relevance

Example format: ["Assessment 1", "Assessment 2", ...]
"""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Extract JSON from response
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        selected_names = json.loads(result_text)
        
        # Reorder candidates based on LLM selection
        reranked = []
        for name in selected_names[:10]:
            for candidate in candidates:
                if candidate["name"] == name:
                    reranked.append(candidate)
                    break
        
        return reranked
    except Exception as e:
        print(f"LLM reranking error: {e}")
        # Fallback to original order
        return candidates[:10]

def enhance_query(query: str) -> str:
    """Use Gemini to enhance and expand the query for better retrieval."""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""Extract key skills, competencies, and assessment requirements from this job query.
Return a comma-separated list of relevant keywords and phrases for searching assessments.

Query: {query}

Focus on:
- Technical skills (e.g., Java, Python, SQL)
- Soft skills (e.g., collaboration, leadership, communication)
- Cognitive abilities (e.g., problem-solving, analytical thinking)
- Personality traits (e.g., conscientiousness, teamwork)
- Job level (e.g., entry-level, mid-level, senior)

Return only the keywords, separated by commas."""

    try:
        response = model.generate_content(prompt)
        enhanced = response.text.strip()
        return f"{query} {enhanced}"
    except Exception as e:
        print(f"Query enhancement error: {e}")
        return query

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint to verify API is running."""
    return HealthResponse(
        status="healthy",
        message="SHL Assessment Recommendation API is running"
    )

@app.post("/recommend", response_model=RecommendResponse)
async def recommend_assessments(request: QueryRequest):
    """
    Recommend relevant SHL assessments based on a job query.
    
    Returns 5-10 most relevant assessments with balanced recommendations.
    """
    import time
    start_time = time.time()
    
    try:
        query = request.query.strip()
        
        if not query:
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        # Enhance query using LLM
        enhanced_query = enhance_query(query)
        
        # Vector search using ChromaDB
        results = collection.query(
            query_texts=[enhanced_query],
            n_results=min(30, collection.count())
        )
        
        if not results["ids"] or len(results["ids"][0]) == 0:
            raise HTTPException(status_code=404, detail="No assessments found")
        
        # Format candidates
        candidates = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            candidates.append({
                "id": doc_id,
                "name": metadata.get("name", "Unknown"),
                "url": metadata.get("url", ""),
                "description": metadata.get("description", ""),
                "test_type": metadata.get("test_type", ""),
                "score": 1 - results["distances"][0][i]  # Convert distance to similarity
            })
        
        # Use LLM for reranking and balancing
        reranked = query_llm_for_reranking(query, candidates)
        
        # Ensure we have at least 5, at most 10 recommendations
        final_results = reranked[:10]
        if len(final_results) < 5 and len(candidates) >= 5:
            final_results = candidates[:5]
        
        # Format response
        recommendations = [
            AssessmentRecommendation(
                assessment_name=r["name"],
                url=r["url"],
                score=r.get("score", 0.0)
            )
            for r in final_results
        ]
        
        processing_time = time.time() - start_time
        
        return RecommendResponse(
            query=query,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "SHL Assessment Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "recommend": "/recommend (POST)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)