"""
Qdrant Vector Repository.

Implementation of VectorRepository using Qdrant.
"""

import asyncio
import logging
from typing import Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.exceptions import VectorStoreError

logger = logging.getLogger(__name__)


class QdrantVectorRepository(VectorRepository):
    """Qdrant implementation of VectorRepository."""

    def __init__(self, url: str, api_key: Optional[str] = None, prefer_grpc: bool = False, timeout: int = 30) -> None:
        """Initialize the Qdrant client."""
        if url == ":memory:":
            self._client = QdrantClient(location=":memory:")
        else:
            self._client = QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc, timeout=timeout)

    async def create_collection(self, name: str, dimension: int, distance_metric: str = "Cosine") -> None:
        """Create a new vector collection.

        Args:
            name: Collection name.
            dimension: Vector dimension.
            distance_metric: Distance metric ('Cosine', 'Euclidean', 'Dot').
        """
        distance_map = {
            "Cosine": models.Distance.COSINE,
            "Euclidean": models.Distance.EUCLID,
            "Dot": models.Distance.DOT,
        }
        dist = distance_map.get(distance_metric, models.Distance.COSINE)

        def sync_create():
            self._client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(size=dimension, distance=dist),
            )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_create)
            logger.info("Created Qdrant collection: %s", name)
        except Exception as e:
            raise VectorStoreError("create_collection", str(e))

    async def list_collections(self) -> list[str]:
        """List all collections."""
        def sync_list():
            return [c.name for c in self._client.get_collections().collections]
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, sync_list)
        except Exception as e:
            raise VectorStoreError("list_collections", str(e))

    async def collection_exists(self, name: str) -> bool:
        """Check if a collection exists."""
        def sync_exists():
            return self._client.collection_exists(collection_name=name)

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, sync_exists)
        except Exception as e:
            raise VectorStoreError("collection_exists", str(e))

    async def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        def sync_delete():
            self._client.delete_collection(collection_name=name)

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_delete)
            logger.info("Deleted Qdrant collection: %s", name)
        except Exception as e:
            raise VectorStoreError("delete_collection", str(e))

    async def upsert_vectors(self, collection: str, vectors: list[tuple[str, list[float], dict]]) -> None:
        """Upsert vectors into a collection.

        Args:
            collection: Collection name.
            vectors: List of tuples (id, vector, payload).
        """
        points = [
            models.PointStruct(id=vid, vector=vec, payload=payload)
            for vid, vec, payload in vectors
        ]

        def sync_upsert():
            self._client.upsert(
                collection_name=collection,
                points=points,
            )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_upsert)
        except Exception as e:
            raise VectorStoreError("upsert_vectors", str(e))

    async def search(self, collection: str, query_vector: list[float], limit: int = 10, filters: Optional[dict] = None) -> list[dict]:
        """Search for similar vectors."""
        # Note: In a full implementation, we'd map the generic filters dict to Qdrant's Filter objects
        qdrant_filter = None
        
        def sync_search():
            return self._client.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )

        loop = asyncio.get_event_loop()
        try:
            results = await loop.run_in_executor(None, sync_search)
            return [
                {
                    "id": res.id,
                    "score": res.score,
                    "payload": res.payload
                }
                for res in results
            ]
        except Exception as e:
            raise VectorStoreError("search", str(e))

    async def delete_vectors(self, collection: str, vector_ids: list[str]) -> None:
        """Delete specific vectors from a collection."""
        def sync_delete():
            self._client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(points=vector_ids),
            )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_delete)
        except Exception as e:
            raise VectorStoreError("delete_vectors", str(e))

    async def update_payload(self, collection: str, vector_id: str, payload: dict) -> None:
        """Update the payload of a specific vector."""
        def sync_update():
            self._client.set_payload(
                collection_name=collection,
                payload=payload,
                points=[vector_id],
            )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_update)
        except Exception as e:
            raise VectorStoreError("update_payload", str(e))

    async def batch_update_payload(self, collection: str, updates: list[tuple[str, dict]]) -> None:
        """Update payloads for multiple vectors."""
        # Process in chunks or sequentially
        loop = asyncio.get_event_loop()
        for vector_id, payload in updates:
            def sync_update(vid=vector_id, pld=payload):
                self._client.set_payload(
                    collection_name=collection,
                    payload=pld,
                    points=[vid],
                )
            try:
                await loop.run_in_executor(None, sync_update)
            except Exception as e:
                logger.error("Failed to update payload for point %s: %s", vector_id, e)
                raise VectorStoreError("batch_update_payload", str(e))

    async def create_alias(self, collection: str, alias: str) -> None:
        """Create an alias for a collection."""
        def sync_alias():
            self._client.update_collection_aliases(
                change_aliases_operations=[
                    models.CreateAliasOperation(
                        create_alias=models.CreateAlias(
                            collection_name=collection,
                            alias_name=alias,
                        )
                    )
                ]
            )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_alias)
        except Exception as e:
            raise VectorStoreError("create_alias", str(e))

    async def switch_alias(self, alias: str, new_collection: str) -> None:
        """Atomically switch an alias to point to a new collection."""
        def sync_switch():
            # Get current collection for alias to remove it
            try:
                # Need to use raw API to find what alias points to, or just delete and create
                # Qdrant aliases can be swapped atomically by sending both ops in one list
                # Wait, to do it cleanly, we can just delete the old alias and create new in one transaction
                self._client.update_collection_aliases(
                    change_aliases_operations=[
                        models.DeleteAliasOperation(
                            delete_alias=models.DeleteAlias(alias_name=alias)
                        ),
                        models.CreateAliasOperation(
                            create_alias=models.CreateAlias(
                                collection_name=new_collection,
                                alias_name=alias,
                            )
                        )
                    ]
                )
            except Exception:
                # If alias didn't exist, just create it
                self._client.update_collection_aliases(
                    change_aliases_operations=[
                        models.CreateAliasOperation(
                            create_alias=models.CreateAlias(
                                collection_name=new_collection,
                                alias_name=alias,
                            )
                        )
                    ]
                )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_switch)
        except Exception as e:
            raise VectorStoreError("switch_alias", str(e))

    async def delete_alias(self, alias: str) -> None:
        """Delete a collection alias."""
        def sync_delete():
            self._client.update_collection_aliases(
                change_aliases_operations=[
                    models.DeleteAliasOperation(
                        delete_alias=models.DeleteAlias(alias_name=alias)
                    )
                ]
            )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_delete)
        except Exception as e:
            raise VectorStoreError("delete_alias", str(e))

    async def optimize_collection(self, name: str) -> None:
        """Trigger index optimization."""
        def sync_optimize():
            self._client.update_collection(
                collection_name=name,
                optimizer_config=models.OptimizersConfigDiff(deleted_threshold=0.2)
            )
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, sync_optimize)
        except Exception as e:
            raise VectorStoreError("optimize_collection", str(e))

    async def get_collection_info(self, name: str) -> dict:
        """Get collection information."""
        def sync_info():
            info = self._client.get_collection(collection_name=name)
            return {
                "status": str(info.status),
                "points_count": info.points_count,
                "vectors_count": getattr(info, "vectors_count", info.points_count),
            }

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, sync_info)
        except Exception as e:
            raise VectorStoreError("get_collection_info", str(e))

    async def count(self, collection: str) -> int:
        """Count the number of vectors in a collection."""
        def sync_count():
            return self._client.count(collection_name=collection).count

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, sync_count)
        except Exception as e:
            raise VectorStoreError("count", str(e))

    async def scroll(
        self, 
        collection: str, 
        limit: int = 100, 
        offset: Optional[Any] = None
    ) -> tuple[list[dict[str, Any]], Any]:
        """Scroll over vectors in a collection to retrieve them in batches."""
        def sync_scroll():
            return self._client.scroll(
                collection_name=collection,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )

        loop = asyncio.get_event_loop()
        try:
            results, next_page_offset = await loop.run_in_executor(None, sync_scroll)
            return [
                {
                    "id": res.id,
                    "payload": res.payload
                }
                for res in results
            ], next_page_offset
        except Exception as e:
            raise VectorStoreError("scroll", str(e))
