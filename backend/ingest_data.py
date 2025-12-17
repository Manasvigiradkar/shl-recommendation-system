"""
Data Ingestion Script - Load SHL assessments into ChromaDB
"""

import json
import chromadb
from chromadb.utils import embedding_functions
import os
from typing import Dict

# ---------- PATH SETUP ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "shl_assessments.json")
CHROMA_PATH = os.path.join(BASE_DIR, "..", "chroma_db")


# ---------- METADATA SANITIZER ----------
def sanitize_value(value):
    """
    ChromaDB metadata must be scalar (str, int, float, bool, None)
    This function converts lists/dicts safely to strings
    """
    if isinstance(value, list):
        return ", ".join(map(str, value))
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


# ---------- DOCUMENT BUILDER ----------
def create_document_text(assessment: Dict) -> str:
    parts = []

    if assessment.get("name"):
        parts.append(f"Assessment: {assessment['name']}")

    if assessment.get("description"):
        parts.append(f"Description: {assessment['description']}")

    test_type_map = {
        "K": "Knowledge and Skills Assessment",
        "P": "Personality and Behavior Assessment",
        "C": "Cognitive Ability Assessment",
        "S": "Situational Judgment Test",
        "O": "General Assessment",
    }
    test_type = assessment.get("test_type", "O")
    parts.append(f"Type: {test_type_map.get(test_type, 'General Assessment')}")

    if assessment.get("category"):
        parts.append(f"Category: {sanitize_value(assessment['category'])}")

    if assessment.get("skills"):
        parts.append(f"Skills: {sanitize_value(assessment['skills'])}")

    if assessment.get("level"):
        parts.append(f"Level: {assessment['level']}")

    if assessment.get("duration") and assessment["duration"] != "N/A":
        parts.append(f"Duration: {assessment['duration']}")

    return " | ".join(parts)


# ---------- INGEST FUNCTION ----------
def ingest_data():
    print(f"Loading data from {DATA_PATH}...")

    if not os.path.exists(DATA_PATH):
        print("❌ shl_assessments.json not found. Run scraper first.")
        return

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        assessments = json.load(f)

    print(f"✅ Loaded {len(assessments)} assessments")

    # ---------- EMBEDDINGS ----------
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Delete old collection if exists
    try:
        chroma_client.delete_collection("shl_assessments")
        print("🗑️ Old collection removed")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="shl_assessments",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"},
    )

    ids, documents, metadatas = [], [], []

    for idx, assessment in enumerate(assessments):
        ids.append(f"assessment_{idx}")
        documents.append(create_document_text(assessment))

        metadatas.append({
            "name": sanitize_value(assessment.get("name", "Unknown")),
            "url": sanitize_value(assessment.get("url", "")),
            "test_type": sanitize_value(assessment.get("test_type", "O")),
            "category": sanitize_value(assessment.get("category", "General")),
            "level": sanitize_value(assessment.get("level", "All Levels")),
        })

    print("🚀 Ingesting into ChromaDB...")
    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"✅ Ingestion complete. Total docs: {collection.count()}")

    # ---------- QUICK TEST ----------
    print("\n🔎 Test query:")
    results = collection.query(
        query_texts=["Java developer with communication skills"],
        n_results=3,
    )

    for i, meta in enumerate(results["metadatas"][0]):
        print(f"{i+1}. {meta['name']}")


# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    ingest_data()
