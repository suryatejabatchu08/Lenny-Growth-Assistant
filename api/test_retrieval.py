"""
Test script for retrieval service
"""
import os
import sys
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.retrieval import get_retrieval_service, retrieve_transcripts

def test_retrieval_service():
    """Test the retrieval service"""
    # Load environment variables
    load_dotenv()

    # Check if database URL is set
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("WARNING: DATABASE_URL not set in environment")
        print("Please set up the database and run ingestion first")
        return False

    try:
        # Get retrieval service
        service = get_retrieval_service()
        print("Retrieval service initialized successfully")

        # Test embedding
        test_text = "What do top PMs think about activation?"
        embedding = service.embed_query(test_text)
        print(f"Generated embedding of length: {len(embedding)}")

        # Test retrieval (will likely return empty if no data ingested yet)
        chunks, context = service.retrieve_context("activation strategies for PLG products")
        print(f"Retrieved {len(chunks)} chunks")
        if chunks:
            print(f"First chunk similarity: {chunks[0].get('similarity_score', 0):.3f}")
            print(f"Context preview: {context[:200] if context else 'None'}...")
        else:
            print("No chunks retrieved (expected if database is empty)")

        return True

    except Exception as e:
        print(f"Error testing retrieval service: {e}")
        return False

if __name__ == "__main__":
    success = test_retrieval_service()
    if success:
        print("Retrieval service test completed")
    else:
        print("Retrieval service test failed")
        sys.exit(1)