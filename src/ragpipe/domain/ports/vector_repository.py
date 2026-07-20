"""Vector repository port interface for the RAG Data Ingestion Platform.

This module defines the abstract base class for interacting with vector
databases (e.g. Qdrant, Pinecone, Milvus).  The domain layer depends only
on this abstraction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class VectorRepository(ABC):
    """Abstract interface for vector database operations.

    Covers collection management, CRUD on vectors, search, payload updates,
    and alias management for zero-downtime index switching.
    """

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------

    @abstractmethod
    def create_collection(
        self,
        name: str,
        dimension: int,
        distance_metric: str = "cosine",
    ) -> None:
        """Create a new vector collection.

        Args:
            name: Collection name.
            dimension: Vector dimensionality.
            distance_metric: Distance metric (``cosine``, ``euclidean``,
                ``dot``).
        """

    @abstractmethod
    def list_collections(self) -> list[str]:
        """List all vector collections."""

    @abstractmethod
    def collection_exists(self, name: str) -> bool:
        """Check whether a collection exists.

        Args:
            name: Collection name.

        Returns:
            ``True`` if the collection exists.
        """

    @abstractmethod
    def delete_collection(self, name: str) -> None:
        """Delete a collection and all its vectors.

        Args:
            name: Collection name.
        """

    @abstractmethod
    def optimize_collection(self, name: str) -> None:
        """Trigger index optimization on the collection."""

    @abstractmethod
    def get_collection_info(self, name: str) -> dict[str, object]:
        """Retrieve metadata about a collection.

        Args:
            name: Collection name.

        Returns:
            Dictionary containing collection metadata (implementation-defined).
        """

    @abstractmethod
    def count(self, collection: str) -> int:
        """Return the number of vectors in a collection.

        Args:
            collection: Collection name.

        Returns:
            Non-negative vector count.
        """

    # ------------------------------------------------------------------
    # Vector CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    def upsert_vectors(
        self,
        collection: str,
        vectors: list[tuple[str, list[float], dict[str, object]]],
    ) -> None:
        """Insert or update vectors in a collection.

        Args:
            collection: Collection name.
            vectors: List of ``(vector_id, vector, payload)`` tuples.
        """

    @abstractmethod
    def delete_vectors(
        self,
        collection: str,
        vector_ids: list[str],
    ) -> None:
        """Delete vectors by their identifiers.

        Args:
            collection: Collection name.
            vector_ids: List of vector identifiers to delete.
        """

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    @abstractmethod
    def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        filters: Optional[dict[str, object]] = None,
    ) -> list[dict[str, object]]:
        """Perform a nearest-neighbour search.

        Args:
            collection: Collection name.
            query_vector: Query vector.
            limit: Maximum number of results.
            filters: Optional payload-based filters.

        Returns:
            List of result dicts, each containing at least ``id``, ``score``,
            and ``payload`` keys.
        """

    # ------------------------------------------------------------------
    # Payload management
    # ------------------------------------------------------------------

    @abstractmethod
    def update_payload(
        self,
        collection: str,
        vector_id: str,
        payload: dict[str, object],
    ) -> None:
        """Update the payload of a single vector.

        Args:
            collection: Collection name.
            vector_id: Vector identifier.
            payload: New payload fields to merge.
        """

    @abstractmethod
    def batch_update_payload(
        self,
        collection: str,
        updates: list[tuple[str, dict[str, object]]],
    ) -> None:
        """Update payloads for multiple vectors in a single call.

        Args:
            collection: Collection name.
            updates: List of ``(vector_id, payload)`` tuples.
        """

    # ------------------------------------------------------------------
    # Alias management (zero-downtime index switching)
    # ------------------------------------------------------------------

    @abstractmethod
    def create_alias(self, collection: str, alias: str) -> None:
        """Create an alias pointing to a collection.

        Args:
            collection: The target collection name.
            alias: The alias name.
        """

    @abstractmethod
    def switch_alias(self, alias: str, new_collection: str) -> None:
        """Atomically switch an alias to point to a different collection.

        Args:
            alias: The alias name.
            new_collection: The new target collection name.
        """

    @abstractmethod
    def delete_alias(self, alias: str) -> None:
        """Delete an alias.

        Args:
            alias: The alias name to remove.
        """

    @abstractmethod
    def scroll(
        self, 
        collection: str, 
        limit: int = 100, 
        offset: Optional[Any] = None
    ) -> tuple[list[dict[str, Any]], Any]:
        """Scroll over vectors in a collection to retrieve them in batches.

        Args:
            collection: The collection name.
            limit: Maximum number of vectors to return.
            offset: Pagination offset object to resume from.

        Returns:
            A tuple of (results, next_page_offset).
        """
