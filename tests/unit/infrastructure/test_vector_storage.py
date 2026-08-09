import asyncio
from unittest.mock import MagicMock, patch
import pytest

from ragpipe.infrastructure.vector.qdrant_repository import QdrantVectorRepository
from ragpipe.domain.exceptions import VectorStoreError

@pytest.fixture
def mock_qdrant_client():
    with patch("ragpipe.infrastructure.vector.qdrant_repository.QdrantClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client

@pytest.fixture
def vector_repo(mock_qdrant_client):
    return QdrantVectorRepository(url="http://localhost:6333", api_key="test-key")

@pytest.mark.asyncio
async def test_upsert_vectors(vector_repo, mock_qdrant_client):
    collection_name = "test-collection"
    vectors = [
        ("id-1", [0.1, 0.2, 0.3], {"text": "chunk 1", "index": 0}),
        ("id-2", [0.4, 0.5, 0.6], {"text": "chunk 2", "index": 1})
    ]
    
    # Store vectors
    await vector_repo.upsert_vectors(collection_name, vectors)
    
    # Check that client.upsert was called correctly
    mock_qdrant_client.upsert.assert_called_once()
    call_args = mock_qdrant_client.upsert.call_args[1]
    
    assert call_args["collection_name"] == collection_name
    points = call_args["points"]
    assert len(points) == 2
    
    # Verify vector ids, embeddings, and payloads
    assert points[0].id == "id-1"
    assert points[0].vector == [0.1, 0.2, 0.3]
    assert points[0].payload == {"text": "chunk 1", "index": 0}
    
    assert points[1].id == "id-2"
    assert points[1].vector == [0.4, 0.5, 0.6]
    assert points[1].payload == {"text": "chunk 2", "index": 1}

@pytest.mark.asyncio
async def test_upsert_vectors_failure_raises_vector_store_error(vector_repo, mock_qdrant_client):
    mock_qdrant_client.upsert.side_effect = Exception("Connection lost")
    
    with pytest.raises(VectorStoreError) as exc_info:
        await vector_repo.upsert_vectors(
            collection="test-collection",
            vectors=[("id-1", [0.1, 0.2, 0.3], {"text": "chunk 1"})]
        )
        
    assert "Connection lost" in str(exc_info.value)
    assert exc_info.value.operation == "upsert_vectors"

@pytest.mark.asyncio
async def test_delete_vectors(vector_repo, mock_qdrant_client):
    vector_ids = ["id-1", "id-2"]
    await vector_repo.delete_vectors("test-collection", vector_ids)
    
    mock_qdrant_client.delete.assert_called_once()
    call_args = mock_qdrant_client.delete.call_args[1]
    assert call_args["collection_name"] == "test-collection"
    # Qdrant deletes by PointIdsList
    points_selector = call_args["points_selector"]
    assert points_selector.points == vector_ids

@pytest.mark.asyncio
async def test_delete_vectors_retry_idempotency(vector_repo, mock_qdrant_client):
    # Idempotent deletion, Qdrant client handles deletion gracefully even if ids don't exist
    vector_ids = ["non-existent-id"]
    await vector_repo.delete_vectors("test-collection", vector_ids)
    
    mock_qdrant_client.delete.assert_called_once()
    call_args = mock_qdrant_client.delete.call_args[1]
    assert call_args["points_selector"].points == vector_ids

@pytest.mark.asyncio
async def test_search(vector_repo, mock_qdrant_client):
    # Setup mock search results
    mock_result_1 = MagicMock()
    mock_result_1.id = "id-1"
    mock_result_1.score = 0.95
    mock_result_1.payload = {"text": "match 1"}
    
    # The actual qdrant object wraps in points
    mock_query_response = MagicMock()
    mock_query_response.points = [mock_result_1]
    
    mock_qdrant_client.query_points.return_value = mock_query_response
    
    results = await vector_repo.search(
        collection="test-collection",
        query_vector=[0.1, 0.2, 0.3],
        limit=5,
        filters={"source": "test"}
    )
    
    assert len(results) == 1
    assert results[0]["id"] == "id-1"
    assert results[0]["score"] == 0.95
    assert results[0]["payload"]["text"] == "match 1"
    
    mock_qdrant_client.query_points.assert_called_once()
    call_args = mock_qdrant_client.query_points.call_args[1]
    assert call_args["collection_name"] == "test-collection"
    assert call_args["query"] == [0.1, 0.2, 0.3]
    assert call_args["limit"] == 5
    assert call_args["with_payload"] is True
