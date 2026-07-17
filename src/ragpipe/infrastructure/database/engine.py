"""
SQLAlchemy Async Engine Setup.

Provides database engine and session factory for the application.
Supports SQLite (development) and PostgreSQL (production).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from ragpipe.config.settings import Settings

logger = logging.getLogger(__name__)


class DatabaseEngine:
    """Manages the SQLAlchemy async engine and session factory.

    Provides methods to create and dispose of database connections,
    and a context manager for obtaining database sessions.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize database engine.

        Args:
            settings: Application settings containing database configuration.
        """
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get the SQLAlchemy async engine.

        Returns:
            The async engine instance.

        Raises:
            RuntimeError: If engine has not been initialized.
        """
        if self._engine is None:
            raise RuntimeError("Database engine not initialized. Call initialize() first.")
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory.

        Returns:
            The async session factory.

        Raises:
            RuntimeError: If engine has not been initialized.
        """
        if self._session_factory is None:
            raise RuntimeError("Database engine not initialized. Call initialize() first.")
        return self._session_factory

    async def initialize(self) -> None:
        """Initialize the database engine and session factory.

        Creates the async engine with appropriate pool configuration
        based on the database URL (SQLite vs PostgreSQL).
        """
        db_url = self._settings.database.database_url
        is_sqlite = "sqlite" in db_url

        engine_kwargs: dict = {
            "echo": self._settings.debug and self._settings.log_level == "DEBUG",
        }

        if is_sqlite:
            # SQLite doesn't support connection pooling well
            engine_kwargs["poolclass"] = NullPool
            # Required for SQLite async
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["poolclass"] = QueuePool
            engine_kwargs["pool_size"] = self._settings.database.db_pool_size
            engine_kwargs["max_overflow"] = self._settings.database.db_max_overflow
            engine_kwargs["pool_recycle"] = self._settings.database.db_pool_recycle
            engine_kwargs["pool_pre_ping"] = True

        self._engine = create_async_engine(db_url, **engine_kwargs)

        if is_sqlite:
            from sqlalchemy import event
            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(
            "Database engine initialized",
            extra={"database_url": db_url.split("@")[-1] if "@" in db_url else db_url},
        )

    async def create_tables(self) -> None:
        """Create all database tables.

        Uses the ORM metadata to create tables that don't exist yet.
        In production, use Alembic migrations instead.
        """
        from ragpipe.infrastructure.database.models import Base

        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    async def dispose(self) -> None:
        """Dispose of the database engine and close all connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database engine disposed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session as an async context manager.

        Yields:
            An async database session.

        Raises:
            RuntimeError: If engine has not been initialized.
        """
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
