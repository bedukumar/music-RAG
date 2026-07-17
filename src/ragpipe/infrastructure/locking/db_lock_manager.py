"""
Database Lock Manager.

Distributed locking using the database.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ragpipe.domain.ports.lock_manager import LockManager
from ragpipe.infrastructure.database.models import LockORM


class DatabaseLockManager(LockManager):
    """Database-backed distributed lock manager."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with a database session."""
        self._session = session

    async def acquire(self, resource_id: str, owner_id: str, ttl_seconds: int = 60) -> bool:
        """Acquire a lock on a resource.

        Args:
            resource_id: The resource to lock.
            owner_id: The identifier of the lock owner.
            ttl_seconds: Time to live in seconds.

        Returns:
            True if acquired, False otherwise.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)

        # First, try to clean up expired lock for this resource
        await self._session.execute(
            delete(LockORM).where(
                LockORM.resource_id == resource_id,
                LockORM.expires_at < now,
            )
        )
        await self._session.flush()

        # Try to insert new lock
        try:
            lock = LockORM(
                resource_id=resource_id,
                owner_id=owner_id,
                expires_at=expires_at,
            )
            self._session.add(lock)
            await self._session.flush()
            return True
        except IntegrityError:
            # Lock already exists and is not expired
            await self._session.rollback()
            return False

    async def release(self, resource_id: str, owner_id: str) -> bool:
        """Release a lock.

        Args:
            resource_id: The locked resource.
            owner_id: The owner releasing the lock.

        Returns:
            True if released, False if not owned by owner.
        """
        result = await self._session.execute(
            delete(LockORM).where(
                LockORM.resource_id == resource_id,
                LockORM.owner_id == owner_id,
            )
        )
        await self._session.flush()
        return result.rowcount > 0

    async def force_release(self, resource_id: str) -> bool:
        """Forcibly release a lock on a resource regardless of owner.

        Args:
            resource_id: Identifier of the resource.

        Returns:
            True if a lock was released, False if no lock was held.
        """
        result = await self._session.execute(
            delete(LockORM).where(
                LockORM.resource_id == resource_id,
            )
        )
        await self._session.flush()
        return result.rowcount > 0

    async def is_locked(self, resource_id: str) -> bool:
        """Check if a resource is currently locked.

        Args:
            resource_id: The resource to check.

        Returns:
            True if locked.
        """
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(LockORM).where(
                LockORM.resource_id == resource_id,
                LockORM.expires_at > now,
            )
        )
        return result.scalar_one_or_none() is not None

    async def extend(self, resource_id: str, owner_id: str, ttl_seconds: int = 60) -> bool:
        """Extend a lock's TTL.

        Args:
            resource_id: The locked resource.
            owner_id: The lock owner.
            ttl_seconds: Additional time to live from now.

        Returns:
            True if extended, False if not owned or doesn't exist.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        
        result = await self._session.execute(
            update(LockORM)
            .where(
                LockORM.resource_id == resource_id,
                LockORM.owner_id == owner_id,
            )
            .values(expires_at=expires_at)
        )
        await self._session.flush()
        return result.rowcount > 0
