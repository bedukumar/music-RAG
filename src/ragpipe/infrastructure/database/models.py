"""
SQLAlchemy ORM Models.

Defines the relational database schema for the Audio RAG platform.
These ORM models map to the domain models but are kept separate
to maintain clean architecture boundaries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def _uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class MediaItemORM(Base):
    """ORM model for media items (Songs, Podcasts, Videos)."""

    __tablename__ = "media_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    album: Mapped[str | None] = mapped_column(String(255), nullable=True)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[dict] = mapped_column(JSON, default=list)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_fields: Mapped[dict] = mapped_column(JSON, default=dict)

    # Song-specific fields
    lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    musical_key: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Podcast-specific fields
    show_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    episode_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guests: Mapped[dict] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Video-specific fields
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    video_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Relationships
    modality_statuses: Mapped[list["ModalityStatusORM"]] = relationship(
        back_populates="media_item", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["JobORM"]] = relationship(
        back_populates="media_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_media_type_created", "media_type", "created_at"),
        Index("idx_media_title", "title"),
    )


class ModalityStatusORM(Base):
    """ORM model for tracking per-modality processing status."""

    __tablename__ = "modality_statuses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    media_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False
    )
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    data_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    embedding_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    embedding_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    last_processed: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    media_item: Mapped["MediaItemORM"] = relationship(back_populates="modality_statuses")

    __table_args__ = (
        UniqueConstraint("media_id", "modality", name="uq_media_modality"),
        Index("idx_modality_status", "modality", "embedding_status"),
        Index("idx_media_modality", "media_id", "modality"),
    )


class EmbeddingVersionORM(Base):
    """ORM model for embedding version tracking."""

    __tablename__ = "embedding_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    chunking_strategy: Mapped[str] = mapped_column(String(100), nullable=False)
    chunking_version: Mapped[str] = mapped_column(String(50), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_embedding_version_modality_active", "modality", "is_active"),
    )


class EmbeddingRecordORM(Base):
    """ORM model for tracking individual embedding records."""

    __tablename__ = "embedding_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    media_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False
    )
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("embedding_versions.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_id: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_embedding_record_media_modality", "media_id", "modality"),
        Index("idx_embedding_record_version", "version_id"),
        UniqueConstraint("media_id", "modality", "version_id", "chunk_index",
                         name="uq_embedding_record"),
    )


class JobORM(Base):
    """ORM model for pipeline jobs."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    media_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("media_items.id", ondelete="CASCADE"), nullable=False
    )
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    pipeline_state_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Relationships
    media_item: Mapped["MediaItemORM"] = relationship(back_populates="jobs")

    __table_args__ = (
        Index("idx_job_status", "status"),
        Index("idx_job_media_modality", "media_id", "modality"),
        Index("idx_job_priority_created", "priority", "created_at"),
    )


class PipelineStateORM(Base):
    """ORM model for pipeline execution state."""

    __tablename__ = "pipeline_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    media_id: Mapped[str] = mapped_column(String(36), nullable=False)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    stages: Mapped[dict] = mapped_column(JSON, default=list)
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    overall_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    __table_args__ = (
        Index("idx_pipeline_state_media_modality", "media_id", "modality"),
        Index("idx_pipeline_state_job", "job_id"),
    )


class MigrationORM(Base):
    """ORM model for index migration tracking."""

    __tablename__ = "migrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    from_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    to_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    total_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_items: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_migration_modality_status", "modality", "status"),
    )


class LockORM(Base):
    """ORM model for distributed locks."""

    __tablename__ = "distributed_locks"

    resource_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ConversationORM(Base):
    """ORM model for persisted conversations."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    memory_window: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    messages: Mapped[list["ConversationMessageORM"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessageORM.created_at"
    )


class ConversationMessageORM(Base):
    """ORM model for persisted conversation messages."""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    tool_results: Mapped[list] = mapped_column(JSON, default=list)
    retrieval_context: Mapped[list] = mapped_column(JSON, default=list)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    system_prompt_version: Mapped[str] = mapped_column(String(50), default="v1", nullable=False)
    message_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    conversation: Mapped["ConversationORM"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_conversation_messages_conversation_created", "conversation_id", "created_at"),
        Index("idx_conversation_messages_role", "role"),
    )


class BulkUploadORM(Base):
    """ORM model for bulk upload batches.

    Each row in this table represents a single file (CSV or XLSX) that was
    submitted via the bulk upload API.  It is kept entirely separate from the
    existing ``JobORM`` table — a ``BulkUpload`` produces many ``Jobs`` once
    its rows are parsed by the worker.
    """

    __tablename__ = "bulk_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    object_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    rows: Mapped[list["BulkUploadRowORM"]] = relationship(
        back_populates="bulk_upload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_bulk_upload_status", "status"),
        Index("idx_bulk_upload_created", "created_at"),
    )


class BulkUploadRowORM(Base):
    """ORM model for individual row outcomes within a bulk upload batch.

    The unique constraint on ``(bulk_upload_id, row_number)`` is the canonical
    idempotency key used to prevent duplicate processing when an SQS message
    is delivered more than once.
    """

    __tablename__ = "bulk_upload_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    bulk_upload_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bulk_uploads.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    # Nullable FK — only set when the row produced a media record
    media_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Relationships
    bulk_upload: Mapped["BulkUploadORM"] = relationship(back_populates="rows")

    __table_args__ = (
        # Idempotency constraint: same bulk_upload + row_number = same logical work unit
        UniqueConstraint(
            "bulk_upload_id", "row_number", name="uq_bulk_upload_row"
        ),
        Index("idx_bulk_upload_row_status", "bulk_upload_id", "status"),
        Index("idx_bulk_upload_row_lookup", "bulk_upload_id", "row_number"),
    )

