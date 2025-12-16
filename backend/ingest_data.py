"""
Data Ingestion Script - Load SHL assessments into ChromaDB
"""
import json
import chromadb
from chromadb.utils import embedding_functions
import os
from typing import List, Dict

def create_document_text(assessment: Dict) -> str:
    """Create a rich text representation of the assessment for embedding."""
    parts = []
    
    # Name (most important)
    if assessment.get('name'):
        parts.append(f"Assessment: {assessment['name']}")
    
    # Description
    if assessment.get('description'):
        parts.append(f"Description: {assessment['description']}")
    
    # Test type expansion
    test_type_map = {
        'K': 'Knowledge and Skills Assessment',
        'P': 'Personality and Behavior Assessment',
        'C': 'Cognitive Ability Assessment',
        'S': 'Situational Judgment Test',
        'O': 'General Assessment'
    }
    test_type = assessment.get('test_type', 'O')
    parts.append(f"Type: {test_type_map.get(test_type, 'Assessment')}")
    
    # Category
    if assessment.get('category'):
        parts.append(f"Category: {assessment['category']}")
    
    # Skills
    if assessment.get('skills'):
        parts.append(f"Skills: {', '.join(assessment['skills'])}")
    
    # Level
    if assessment.get('level'):
        parts.append(f"Level: {assessment['level']}")
    
    # Duration
    if assessment.get('duration') and assessment['duration'] != 'N/A':
        parts.append(f"Duration: {assessment['duration']}")
    
    return " | ".join(parts)

def ingest_data(json_file: str = 'shl_assessments.json', 
                gemini_api_key: str = None):
    """Ingest assessment data into ChromaDB."""
    
    # Load data
    print(f"Loading data from {json_file}...")
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            assessments = json.load(f)
        print(f"Loaded {len(assessments)} assessments")
    except FileNotFoundError:
        print(f"Error: {json_file} not found. Please run scraper.py first.")
        return
    
    if len(assessments) < 377:
        print(f"Warning: Only {len(assessments)} assessments found. Expected at least 377.")
    
    # Initialize ChromaDB
    print("Initializing ChromaDB...")
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    # Get API key
    if not gemini_api_key:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY not provided")
        return
    
    # Initialize embedding function
    embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
        api_key=gemini_api_key
    )
    
    # Delete existing collection if it exists
    try:
        chroma_client.delete_collection(name="shl_assessments")
        print("Deleted existing collection")
    except:
        pass
    
    # Create new collection
    print("Creating new collection...")
    collection = chroma_client.create_collection(
        name="shl_assessments",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Prepare data for ingestion
    print("Preparing documents for embedding...")
    ids = []
    documents = []
    metadatas = []
    
    for idx, assessment in enumerate(assessments):
        # Create unique ID
        assessment_id = f"assessment_{idx}"
        
        # Create document text for embedding
        doc_text = create_document_text(assessment)
        
        # Prepare metadata (must be simple types)
        metadata = {
            'name': assessment.get('name', 'Unknown'),
            'url': assessment.get('url', ''),
            'test_type': assessment.get('test_type', 'O'),
            'category': assessment.get('category', 'General'),
            'level': assessment.get('level', 'All Levels'),
            'description': assessment.get('description', '')[:500]  # Truncate long descriptions
        }
        
        # Add to lists
        ids.append(assessment_id)
        documents.append(doc_text)
        metadatas.append(metadata)
    
    # Batch ingest (ChromaDB recommends batches of ~100)
    print("Ingesting data into ChromaDB...")
    batch_size = 100
    for i in range(0, len(ids), batch_size):
        batch_end = min(i + batch_size, len(ids))
        print(f"Ingesting batch {i//batch_size + 1} ({i+1}-{batch_end} of {len(ids)})")
        
        collection.add(
            ids=ids[i:batch_end],
            documents=documents[i:batch_end],
            metadatas=metadatas[i:batch_end]
        )
    
    # Verify ingestion
    count = collection.count()
    print(f"\n{'='*50}")
    print(f"Ingestion Complete!")
    print(f"Total documents in collection: {count}")
    print(f"{'='*50}\n")
    
    # Test query
    print("Testing retrieval with sample query...")
    results = collection.query(
        query_texts=["Java developer with good communication skills"],
        n_results=3
    )
    
    print("\nTop 3 results for 'Java developer with good communication skills':")
    for i, doc_id in enumerate(results['ids'][0]):
        metadata = results['metadatas'][0][i]
        distance = results['distances'][0][i]
        print(f"{i+1}. {metadata['name']} (score: {1-distance:.3f})")
        print(f"   URL: {metadata['url']}")
        print(f"   Type: {metadata['test_type']}\n")

def main():
    """Main execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest SHL assessment data into ChromaDB')
    parser.add_argument('--json-file', default='shl_assessments.json',
                       help='Path to JSON file with scraped data')
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY env var)')
    
    args = parser.parse_args()
    
    ingest_data(args.json_file, args.api_key)

if __name__ == "__main__":
    main()