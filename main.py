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
from dotenv import load_dotenv

# ------------------ Load ENV ------------------

load_dotenv()

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)

# ------------------ ChromaDB Init (FINAL FIX) ------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# ⚠️ MUST MATCH ingest_data.py
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

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

print("📦 Total documents in ChromaDB:", collection.count())

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
    return sorted(candidates, key=lambda x: x["score"], reverse=True)

# ------------------ API Endpoints ------------------

@app.get("/")
async def root():
    return {"message": "SHL Assessment Recommendation API is running"}


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        message="API is operational"
    )


@app.post("/recommend", response_model=RecommendResponse)
async def recommend_assessments(request: QueryRequest):
    start_time = time.time()
    query = request.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if collection.count() == 0:
        raise HTTPException(
            status_code=500,
            detail="ChromaDB is empty. Please ingest data first."
        )

    enhanced_query = enhance_query(query)

    results = collection.query(
        query_texts=[enhanced_query],
        n_results=10
    )

    if not results["ids"][0]:
        raise HTTPException(status_code=404, detail="No assessments found")

    candidates = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        candidates.append({
            "name": meta.get("name", "Unknown"),
            "url": meta.get("url", ""),
            "score": round(1 - results["distances"][0][i], 3)
        })

    final_results = safe_rerank(candidates)

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
