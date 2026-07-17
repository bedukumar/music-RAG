"""Lock manager port interface for the RAG Data Ingestion Platform.

This module defines the abstract base class for distributed locking.
Lock implementations prevent concurrent processing of the same resource
(e.g. the same media item for the same modality).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LockManager(ABC):
    """Abstract interface for distributed lock operations.

    Implementations may use Redis, ZooKeeper, database advisory locks, or
    any other mechanism that supports TTL-based ownership semantics.
    """

    @abstractmethod
    def acquire(
        self,
        resource_id: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> bool:
        """Attempt to acquire a lock on a resource.

        Args:
            resource_id: Identifier of the resource to lock.
            owner_id: Identifier of the lock owner (e.g. worker ID).
            ttl_seconds: Time-to-live in seconds.  The lock automatically
                expires after this duration.

        Returns:
            ``True`` if the lock was acquired, ``False`` if it is already
            held by another owner.
        """

    @abstractmethod
    def release(
        self,
        resource_id: str,
        owner_id: str,
    ) -> bool:
        """Release a lock on a resource.

        Only the current owner can release the lock.

        Args:
            resource_id: Identifier of the resource.
            owner_id: Identifier of the lock owner requesting release.

        Returns:
            ``True`` if the lock was released, ``False`` if the caller
            is not the current owner or no lock is held.
        """

    @abstractmethod
    def is_locked(self, resource_id: str) -> bool:
        """Check whether a resource is currently locked.

        Args:
            resource_id: Identifier of the resource.

        Returns:
            ``True`` if the resource is locked.
        """

    @abstractmethod
    def extend(
        self,
        resource_id: str,
        owner_id: str,
        ttl_seconds: int,
    ) -> bool:
        """Extend the TTL of an existing lock.

        Only the current owner can extend the lock.

        Args:
            resource_id: Identifier of the resource.
            owner_id: Identifier of the lock owner requesting extension.
            ttl_seconds: New time-to-live in seconds (from now).

        Returns:
            ``True`` if the lock was extended, ``False`` if the caller
            is not the current owner or no lock is held.
        """
