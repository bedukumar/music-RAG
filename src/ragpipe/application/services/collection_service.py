"""Application service for collection stats and management."""

from __future__ import annotations

from typing import Any

from ragpipe.domain.ports.vector_repository import VectorRepository


class CollectionService:
    """Expose collection-level metadata for tools."""

    def __init__(self, vector_repository: VectorRepository) -> None:
        self.vector_repo = vector_repository

    async def get_collection_stats(self) -> dict[str, Any]:
        collections = self.vector_repo.list_collections()
        return {
            "collections": [
                {
                    "name": name,
                    "exists": self.vector_repo.collection_exists(name),
                    "count": self.vector_repo.count(name),
                    "info": self.vector_repo.get_collection_info(name),
                }
                for name in collections
            ],
            "total_collections": len(collections),
        }

