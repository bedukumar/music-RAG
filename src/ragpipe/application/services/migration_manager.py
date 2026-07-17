"""
Migration Manager Service.

Handles zero-downtime migrations between embedding versions.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Optional

from ragpipe.application.pipelines.base_pipeline import BasePipeline
from ragpipe.domain.events.events import IndexMigrationFinished, IndexMigrationStarted
from ragpipe.domain.models.migration import Migration, MigrationStatus
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.ports.event_bus import EventBus
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.metrics_collector import MetricsCollector
from ragpipe.domain.ports.state_store import StateStore
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.exceptions import MigrationError

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages zero-downtime index migrations."""

    def __init__(
        self,
        state_store: StateStore,
        media_repository: MediaRepository,
        vector_repository: VectorRepository,
        event_bus: EventBus,
        metrics: MetricsCollector,
        pipeline_factory: Callable[[Modality], BasePipeline],
    ) -> None:
        self.state_store = state_store
        self.media_repo = media_repository
        self.vector_repo = vector_repository
        self.event_bus = event_bus
        self.metrics = metrics
        self.pipeline_factory = pipeline_factory

    async def start_backfill(self, modality: Modality, to_version_id: str) -> Migration:
        """Start a backfill migration to a new embedding version.

        Args:
            modality: The target modality.
            to_version_id: The ID of the target embedding version.

        Returns:
            The created Migration record.
        """
        active_version = await self.state_store.get_active_embedding_version(modality)
        from_version_id = active_version.id if active_version else None
        
        target_version = await self.state_store.get_embedding_version(to_version_id)
        if not target_version:
            raise MigrationError("start", f"Target version not found: {to_version_id}")
            
        # Create new collection for the target version
        new_collection_name = f"{modality.value}_{to_version_id}"
        if not await self.vector_repo.collection_exists(new_collection_name):
            # We assume metric is always Cosine here, but it could be configurable on EmbeddingVersion
            await self.vector_repo.create_collection(
                name=new_collection_name,
                dimension=target_version.dimension,
                distance_metric="Cosine"
            )
            
        # Count items to process (all media with data for this modality)
        # Note: MediaRepo list_all doesn't filter by modality data availability easily, 
        # so we'll just say total is total media count for simplicity or get an exact count.
        items, total_media = await self.media_repo.list_all(offset=0, limit=1)
        
        now = datetime.now(timezone.utc)
        migration = Migration(
            id=str(uuid.uuid4()),
            modality=modality,
            from_version_id=from_version_id,
            to_version_id=to_version_id,
            status=MigrationStatus.RUNNING,
            total_items=total_media,
            processed_items=0,
            failed_items=0,
            started_at=now,
            completed_at=None,
            error_message=None,
        )
        await self.state_store.save_migration(migration)
        
        await self.event_bus.publish(IndexMigrationStarted(
            migration_id=migration.id,
            modality=modality.value,
            from_version=from_version_id,
            to_version=to_version_id,
        ))
        
        # Start background processing (fire and forget for this simplistic implementation)
        asyncio.create_task(self._process_backfill(migration.id, target_version))
        
        return migration

    async def _process_backfill(self, migration_id: str, target_version) -> None:
        """Background task to process the backfill."""
        # This is a simplified backfill that just reprocesses everything
        # In a real system, you'd use a robust worker pool and track progress more precisely
        try:
            migration = await self.state_store.get_migration(migration_id)
            if not migration:
                return
                
            # Temporarily replace the pipeline factory's version to the target version
            # A better design would pass the target version to the orchestrator or pipeline
            pipeline = self.pipeline_factory(migration.modality)
            pipeline.embedding_version = target_version
            
            # Fetch all media IDs (simplification: fetching all at once, bad for millions)
            offset = 0
            limit = 100
            
            while True:
                media_items, _ = await self.media_repo.list_all(offset=offset, limit=limit)
                if not media_items:
                    break
                    
                for media in media_items:
                    status = await self.media_repo.get_modality_status(media.id, migration.modality)
                    if status and status.data_available:
                        # Mock Job creation for pipeline execution
                        from ragpipe.domain.models.pipeline import Job
                        from ragpipe.domain.models.modality import ProcessingStatus
                        
                        job = Job(
                            id=str(uuid.uuid4()),
                            media_id=media.id,
                            modality=migration.modality,
                            status=ProcessingStatus.PENDING,
                            priority=0,
                            created_at=datetime.now(timezone.utc),
                            started_at=None, completed_at=None, error_message=None,
                            retry_count=0, max_retries=1, pipeline_state_id=None
                        )
                        
                        try:
                            await pipeline.execute(media.id, job)
                            migration.processed_items += 1
                        except Exception as e:
                            logger.error("Failed backfill for media %s: %s", media.id, e)
                            migration.failed_items += 1
                            
                    # Update progress periodically
                    if (migration.processed_items + migration.failed_items) % 10 == 0:
                        await self.state_store.update_migration(migration)
                        
                offset += limit
                
            # Completion
            migration.status = MigrationStatus.COMPLETED
            migration.completed_at = datetime.now(timezone.utc)
            await self.state_store.update_migration(migration)
            logger.info("Migration %s completed", migration_id)
            
        except Exception as e:
            logger.exception("Migration %s failed: %s", migration_id, e)
            migration = await self.state_store.get_migration(migration_id)
            if migration:
                migration.status = MigrationStatus.FAILED
                migration.completed_at = datetime.now(timezone.utc)
                migration.error_message = str(e)
                await self.state_store.update_migration(migration)

    async def get_migration_status(self, migration_id: str) -> Optional[Migration]:
        """Get the current status of a migration."""
        return await self.state_store.get_migration(migration_id)

    async def list_migrations(self, modality: Optional[Modality] = None) -> list[Migration]:
        """List migrations."""
        return await self.state_store.list_migrations(modality)

    async def switch_index(self, migration_id: str) -> None:
        """Switch the read alias to the new collection and activate the new version."""
        migration = await self.state_store.get_migration(migration_id)
        if not migration:
            raise MigrationError("switch", "Migration not found")
            
        if migration.status != MigrationStatus.COMPLETED:
            raise MigrationError("switch", f"Migration not completed. Status is {migration.status}")
            
        new_collection = f"{migration.modality.value}_{migration.to_version_id}"
        alias = migration.modality.value
        
        # Switch vector DB alias
        await self.vector_repo.switch_alias(alias=alias, new_collection=new_collection)
        
        # Activate embedding version
        # We need the EmbeddingManager logic here, but since it's just setting is_active, 
        # we can do it via state_store if we have a method, or just assume another service handles it
        active = await self.state_store.get_active_embedding_version(migration.modality)
        if active:
            active.is_active = False
            await self.state_store.save_embedding_version(active)
            
        target = await self.state_store.get_embedding_version(migration.to_version_id)
        if target:
            target.is_active = True
            await self.state_store.save_embedding_version(target)
            
        await self.event_bus.publish(IndexMigrationFinished(
            migration_id=migration.id,
            modality=migration.modality.value,
            status="completed",
        ))

    async def rollback(self, migration_id: str) -> None:
        """Rollback a migration by switching the alias back."""
        migration = await self.state_store.get_migration(migration_id)
        if not migration:
            raise MigrationError("rollback", "Migration not found")
            
        if not migration.from_version_id:
            raise MigrationError("rollback", "No previous version to rollback to")
            
        old_collection = f"{migration.modality.value}_{migration.from_version_id}"
        alias = migration.modality.value
        
        await self.vector_repo.switch_alias(alias=alias, new_collection=old_collection)
        
        active = await self.state_store.get_active_embedding_version(migration.modality)
        if active:
            active.is_active = False
            await self.state_store.save_embedding_version(active)
            
        target = await self.state_store.get_embedding_version(migration.from_version_id)
        if target:
            target.is_active = True
            await self.state_store.save_embedding_version(target)
            
        migration.status = MigrationStatus.ROLLED_BACK
        await self.state_store.update_migration(migration)
