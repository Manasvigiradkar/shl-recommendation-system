"""
SHL Assessment Recommendation System - FastAPI Backend
(STABLE & CHROMADB-SAFE VERSION)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import google.generativeai as genai
import chromadb
from chromadb.utils import embedding_functions
import os
import time

# ------------------ FastAPI Init ------------------

app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="AI-powered assessment recommendation system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Gemini Init ------------------

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "AIzaSyDe2S1VrFIlhTN3YX9KBBDOrPtlYTpeiPo"  # replace with env variable in production
)

genai.configure(api_key=GEMINI_API_KEY)

# ------------------ ChromaDB Init (SAFE) ------------------

# Persistent DB location
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# Embedding function (ONLY used when creating collection)
embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key=GEMINI_API_KEY
)

# ⚠️ IMPORTANT: NEVER pass embedding_function to get_collection
try:
    collection = chroma_client.get_collection(name="shl_assessments")
    print("✅ Loaded existing ChromaDB collection")
except Exception:
    collection = chroma_client.create_collection(
        name="shl_assessments",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    print("✅ Created new ChromaDB collection")

# ------------------ Pydantic Models ------------------

class QueryRequest(BaseModel):
    query: str


class AssessmentRecommendation(BaseModel):
    assessment_name: str
    url: str
    score: Optional[float] = None


class RecommendResponse(BaseModel):
    query: str
    recommendations: List[AssessmentRecommendation]
    processing_time: float


class HealthResponse(BaseModel):
    status: str
    message: str

# ------------------ Helper Functions ------------------

def enhance_query(query: str) -> str:
    """
    Gemini-based query enhancement (FAIL-SAFE).
    If Gemini fails, original query is used.
    """
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Extract key skills from this job description:\n{query}"
        )
        return f"{query} {response.text.strip()}"
    except Exception as e:
        print("⚠️ Query enhancement skipped:", e)
        return query


def safe_rerank(candidates: List[dict]) -> List[dict]:
    """
    Safe reranking based purely on similarity score.
    No LLM dependency → stable.
    """
    return sorted(candidates, key=lambda x: x["score"], reverse=True)

# ------------------ API Endpoints ------------------

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "SHL Assessment Recommendation API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "recommend": "/recommend (POST)"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        message="SHL Assessment Recommendation API is running"
    )


@app.post("/recommend", response_model=RecommendResponse, tags=["Recommendation"])
async def recommend_assessments(request: QueryRequest):
    start_time = time.time()
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # Ensure DB has data
    total_docs = collection.count()
    if total_docs == 0:
        raise HTTPException(
            status_code=500,
            detail="ChromaDB is empty. Please ingest assessment data first."
        )

    # Enhance query safely
    enhanced_query = enhance_query(query)

    # Vector search
    results = collection.query(
        query_texts=[enhanced_query],
        n_results=min(10, total_docs)
    )

    if not results["ids"] or not results["ids"][0]:
        raise HTTPException(status_code=404, detail="No assessments found")

    # Build candidate list
    candidates = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        candidates.append({
            "name": meta.get("name", "Unknown"),
            "url": meta.get("url", ""),
            "score": round(1 - results["distances"][0][i], 3)
        })

    # Rerank safely
    final_results = safe_rerank(candidates)[:10]

    recommendations = [
        AssessmentRecommendation(
            assessment_name=item["name"],
            url=item["url"],
            score=item["score"]
        )
        for item in final_results
    ]

    return RecommendResponse(
        query=query,
        recommendations=recommendations,
        processing_time=round(time.time() - start_time, 3)
    )
