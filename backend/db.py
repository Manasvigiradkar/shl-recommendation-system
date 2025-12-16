import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="./chroma_db")
ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    api_key="your_key"
)

collection = client.get_collection("shl_assessments", embedding_function=ef)

# Test query
results = collection.query(
    query_texts=["Java developer"],
    n_results=5
)

print(results)