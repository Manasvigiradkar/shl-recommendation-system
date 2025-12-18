"""
Data Ingestion Script - Load SHL assessments into ChromaDB
"""

import json
import chromadb
from chromadb.utils import embedding_functions
import os
from typing import Dict

# ---------- PATH SETUP (MATCHES main.py) ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "shl_assessments.json")
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

# ---------- METADATA SANITIZER ----------

def sanitize_value(value):
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

    if assessment.get("skills"):
        parts.append(f"Skills: {sanitize_value(assessment['skills'])}")

    if assessment.get("level"):
        parts.append(f"Level: {assessment['level']}")

    return " | ".join(parts)

# ---------- INGEST FUNCTION ----------

def ingest_data():
    print(f"Loading data from {DATA_PATH}...")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        assessments = json.load(f)

    print(f"✅ Loaded {len(assessments)} assessments")

    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    try:
        chroma_client.delete_collection("shl_assessments")
        print("🗑️ Old collection removed")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="shl_assessments",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )

    ids, documents, metadatas = [], [], []

    for idx, assessment in enumerate(assessments):
        ids.append(f"assessment_{idx}")
        documents.append(create_document_text(assessment))

        metadatas.append({
            "name": sanitize_value(assessment.get("name", "Unknown")),
            "url": sanitize_value(assessment.get("url", "")),
        })

    print("🚀 Ingesting into ChromaDB...")
    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"✅ Ingestion complete. Total docs: {collection.count()}")

# ---------- ENTRY POINT ----------

if __name__ == "__main__":
    ingest_data()
