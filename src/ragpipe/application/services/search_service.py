import uuid
import time
from typing import Dict, Any, List, Optional
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.models.modality import Modality

class SearchService:
    """Service for search validation and tuning."""
    def __init__(self, vector_repo: VectorRepository, media_repo: MediaRepository):
        self.vector_repo = vector_repo
        self.media_repo = media_repo
        self.search_history = []
        self.hyperparameters = {
            "top_k": 10,
            "distance_metric": "cosine",
            "threshold": 0.5
        }

    async def validate_search(self, query: str, modality: Modality, ground_truth_ids: List[str]) -> Dict[str, Any]:
        """Validate search against ground truth IDs."""
        # For a full implementation, the query string would be passed to an embedder model.
        # Since this is a test framework/mock for the API, we will just use a dummy vector.
        query_vector = [0.1] * 512
        
        collection = f"{modality.value}_embeddings"
        
        # Check if collection exists
        exists = await self.vector_repo.collection_exists(collection)
        results = []
        if exists:
            top_k = self.hyperparameters.get("top_k", 10)
            results = await self.vector_repo.search(
                collection=collection,
                query_vector=query_vector,
                limit=top_k
            )
        
        retrieved_ids = [res["payload"].get("media_id") for res in results if "payload" in res]
        hits = [rid for rid in retrieved_ids if rid in ground_truth_ids]
        recall = len(hits) / len(ground_truth_ids) if ground_truth_ids else 0.0
        
        entry = {
            "id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "query": query,
            "modality": modality.value,
            "recall": recall,
            "retrieved_count": len(results)
        }
        self.search_history.append(entry)
        
        return {
            "query": query,
            "recall": recall,
            "hits": hits,
            "results": results
        }

    async def get_history(self) -> List[Dict[str, Any]]:
        return self.search_history

    async def tune_hyperparameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in params.items():
            if k in self.hyperparameters:
                self.hyperparameters[k] = v
        return self.hyperparameters
