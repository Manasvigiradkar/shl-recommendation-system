import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

ef = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
    model_name="models/embedding-001"
)

client = chromadb.Client(
    settings=chromadb.Settings(
        persist_directory="chroma_db"
    )
)

collection = client.get_or_create_collection(
    name="shl_assessments",
    embedding_function=ef
)

collection.add(
    documents=["SHL Cognitive Ability Test for Graduates"],
    ids=["1"]
)

results = collection.query(
    query_texts=["cognitive ability test"],
    n_results=1
)

print(results)
