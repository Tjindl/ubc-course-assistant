# create_vectordb.py
import json
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.documents import Document
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

def load_course_data(filepath='data/raw/ubc_courses.json'):
    """Load course data from JSON"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_documents(courses):
    """Enhanced document creation with better metadata"""
    documents = []
    for course in courses:
        # Add prerequisites to content if available
        prereqs = course.get('prerequisites', '')
        content = (
            f"{course['course_code']} - {course['department']} Course\n"
            f"Description: {course['description']}\n"
            f"Prerequisites: {prereqs}\n"
            f"Department: {course['department']}\n"
            f"Campus: {course['campus']}\n"
            f"Year: {course['year']} {course['session']}"
        )

        metadata = {
            'course_code': course['course_code'],
            'department': course['department'],
            'campus': course['campus'],
            'year': course['year'],
            'session': course['session'],
            'course_level': course['course_code'][-3] if len(course['course_code']) >= 3 else '0',
            'source': 'UBC Course Catalog',
            'full_text': content  # Store full text in metadata
        }

        doc = Document(page_content=content, metadata=metadata)
        documents.append(doc)
    return documents

def create_vector_store(documents, persist_directory='./chroma_db'):
    """Create vector store with ChromaDB"""
    client = chromadb.PersistentClient(path=persist_directory)
    
    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-MiniLM-L3-v2"  # Using a smaller, more stable model
    )
    
    # Create new collection
    collection = client.create_collection(
        name="courses",
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Add documents in smaller batches
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        collection.add(
            ids=[str(j) for j in range(i, i + len(batch))],
            documents=[doc.page_content for doc in batch],
            metadatas=[doc.metadata for doc in batch]
        )
        print(f"Added batch {i//batch_size + 1}/{len(documents)//batch_size + 1}")
    
    return collection

def main():
    print("Loading course data...")
    courses = load_course_data()
    print(f"Loaded {len(courses)} courses")

    print("Creating documents...")
    documents = create_documents(courses)

    print("Creating vector store...")
    collection = create_vector_store(documents)

    # Test using ChromaDB query method
    print("\nTesting vector store...")
    results = collection.query(
        query_texts=["CPSC 110"],
        n_results=3
    )
    
    for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0]), 1):
        print(f"\nResult {i}: {metadata['course_code']}")
        print(doc[:200] + "..." if len(doc) > 200 else doc)

if __name__ == "__main__":
    main()
