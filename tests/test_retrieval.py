"""
Comprehensive tests for the retrieval service
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.retrieval import RetrievalService, get_retrieval_service

def test_retrieval_service_initialization():
    """Test that the retrieval service initializes correctly"""
    with patch('api.retrieval.SentenceTransformer') as mock_st:
        mock_st.return_value = Mock()
        mock_st.return_value.get_sentence_embedding_dimension.return_value = 384

        service = RetrievalService()
        assert service is not None
        assert service.embedding_model_name == "all-MiniLM-L6-v2"
        assert service.default_top_k == 3
        assert service.similarity_threshold == 0.3

def test_embed_query():
    """Test embedding a query"""
    with patch('api.retrieval.SentenceTransformer') as mock_st:
        mock_model = Mock()
        mock_value = Mock()
        mock_value.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = [mock_value]
        mock_st.return_value = mock_model

        service = RetrievalService()
        embedding = service.embed_query("test query")

        assert embedding == [0.1, 0.2, 0.3]

def test_get_retrieval_service_singleton():
    """Test that get_retrieval_service returns a singleton"""
    with patch('api.retrieval.SentenceTransformer'):
        service1 = get_retrieval_service()
        service2 = get_retrieval_service()
        assert service1 is service2

def test_retrieve_context_empty_db():
    """Test retrieving context when database is empty"""
    with patch('api.supabase_client.get_supabase_client') as mock_get_client:
        mock_client = Mock()
        mock_rpc = Mock()
        mock_rpc.execute.return_value = Mock(data=[])
        mock_client.rpc.return_value = mock_rpc
        mock_get_client.return_value = mock_client

        with patch('api.retrieval.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = [Mock(tolist=lambda: [0.1, 0.2, 0.3])]
            mock_st.return_value = mock_model

            service = RetrievalService()
            chunks, context, score = service.retrieve_context("test query")

            assert chunks == []
            assert context is None
            assert score == 0.0

def test_retrieve_context_with_results():
    """Test retrieving context when database has results"""
    with patch('api.supabase_client.get_supabase_client') as mock_get_client:
        mock_client = Mock()
        mock_rpc = Mock()
        mock_rpc.execute.return_value = Mock(data=[{
            'id': 'test-id',
            'episode_slug': 'test-slug',
            'episode_title': 'Test Episode',
            'guest_name': 'Test Guest',
            'source_path': 'episodes/test-slug/transcript.md',
            'approx_timestamp': '00:05:00',
            'content': 'This is test content',
            'similarity': 0.85
        }])
        mock_client.rpc.return_value = mock_rpc
        mock_get_client.return_value = mock_client

        with patch('api.retrieval.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_model.encode.return_value = [Mock(tolist=lambda: [0.1, 0.2, 0.3])]
            mock_st.return_value = mock_model

            service = RetrievalService()
            chunks, context, score = service.retrieve_context("test query", top_k=5)

            assert len(chunks) == 1
            assert chunks[0]['episode_title'] == 'Test Episode'
            assert chunks[0]['similarity'] == 0.85
            assert context is not None
            assert 'Test Episode' in context
            assert 'Test Guest' in context
            assert score == 0.85

if __name__ == "__main__":
    pytest.main([__file__])