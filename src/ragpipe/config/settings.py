"""
RagPipe Configuration Settings.

All configuration is loaded from environment variables with sensible defaults.
Uses pydantic-settings for type-safe configuration management.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database connection settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/ragpipe.db",
        description="SQLAlchemy async database URL",
    )
    db_pool_size: int = Field(default=5, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_recycle: int = Field(default=3600, ge=60)


class QdrantSettings(BaseSettings):
    """Qdrant vector database settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_QDRANT_")

    url: str = Field(default="http://localhost:6333")
    api_key: Optional[str] = Field(default=None)
    grpc_port: int = Field(default=6334)
    prefer_grpc: bool = Field(default=False)
    timeout: int = Field(default=30, ge=1)


class AudioEmbeddingSettings(BaseSettings):
    """Audio embedding model settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_AUDIO_")

    embedding_model: str = Field(default="laion-clap")
    embedding_version: str = Field(default="v1")
    embedding_dimension: int = Field(default=512, ge=1)
    sample_rate: int = Field(default=48000, ge=8000)
    chunk_duration: float = Field(default=30.0, gt=0)
    chunk_overlap: float = Field(default=5.0, ge=0)
    chunking_strategy: str = Field(default="fixed_duration")
    chunking_version: str = Field(default="v1")


class TextEmbeddingSettings(BaseSettings):
    """Text embedding model settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_TEXT_")

    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_version: str = Field(default="v1")
    embedding_dimension: int = Field(default=384, ge=1)
    embedding_batch_size: int = Field(default=32, ge=1)
    chunk_size: int = Field(default=512, ge=1)
    chunk_overlap: int = Field(default=50, ge=0)
    chunking_strategy: str = Field(default="sentence")
    chunking_version: str = Field(default="v1")


class MetadataSettings(BaseSettings):
    """Metadata embedding settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_METADATA_")

    fields: str = Field(
        default="title,artist,album,genre,tags,language,description",
        description="Comma-separated list of metadata fields to embed",
    )
    template: str = Field(
        default="{title} by {artist}. Album: {album}. Genre: {genre}. Tags: {tags}. Language: {language}. {description}",
        description="Template for constructing metadata text",
    )
    chunking_version: str = Field(default="v1")

    @property
    def field_list(self) -> list[str]:
        """Return fields as a list."""
        return [f.strip() for f in self.fields.split(",") if f.strip()]


class StorageSettings(BaseSettings):
    """File storage settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_")

    storage_base_path: str = Field(default="./data/storage")
    audio_storage_path: str = Field(default="./data/storage/audio")
    transcript_storage_path: str = Field(default="./data/storage/transcripts")
    max_audio_size_mb: int = Field(default=500, ge=1)


class PipelineSettings(BaseSettings):
    """Pipeline processing settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_PIPELINE_")

    max_retries: int = Field(default=3, ge=0)
    retry_delay: int = Field(default=5, ge=1)
    worker_count: int = Field(default=4, ge=1)
    batch_size: int = Field(default=10, ge=1)
    version: str = Field(default="v1")


class CLAPSettings(BaseSettings):
    """LAION CLAP specific settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_CLAP_")

    enable_fusion: bool = Field(default=False)
    checkpoint_path: Optional[str] = Field(default=None)


class LockSettings(BaseSettings):
    """Distributed locking settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_LOCK_")

    ttl_seconds: int = Field(default=300, ge=10)
    retry_delay: float = Field(default=1.0, ge=0.1)


class MetricsSettings(BaseSettings):
    """Metrics and observability settings."""

    model_config = SettingsConfigDict(env_prefix="RAGPIPE_METRICS_")

    enabled: bool = Field(default=True)
    port: int = Field(default=9090, ge=1024, le=65535)
    prefix: str = Field(default="ragpipe")


class Settings(BaseSettings):
    """Root application settings aggregating all sub-settings."""

    model_config = SettingsConfigDict(
        env_prefix="RAGPIPE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="ragpipe")
    env: str = Field(default="development")
    debug: bool = Field(default=True)
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1024, le=65535)
    workers: int = Field(default=1, ge=1)
    log_level: str = Field(default="INFO")
    secret_key: str = Field(default="change-me-in-production")

    # Use mock embedders (for dev/testing without GPU)
    use_mock_embedders: bool = Field(default=True)

    # Sub-settings (initialized lazily)
    _database: Optional[DatabaseSettings] = None
    _qdrant: Optional[QdrantSettings] = None
    _audio_embedding: Optional[AudioEmbeddingSettings] = None
    _text_embedding: Optional[TextEmbeddingSettings] = None
    _metadata: Optional[MetadataSettings] = None
    _storage: Optional[StorageSettings] = None
    _pipeline: Optional[PipelineSettings] = None
    _clap: Optional[CLAPSettings] = None
    _lock: Optional[LockSettings] = None
    _metrics: Optional[MetricsSettings] = None

    @property
    def database(self) -> DatabaseSettings:
        """Get database settings."""
        if self._database is None:
            self._database = DatabaseSettings()
        return self._database

    @property
    def qdrant(self) -> QdrantSettings:
        """Get Qdrant settings."""
        if self._qdrant is None:
            self._qdrant = QdrantSettings()
        return self._qdrant

    @property
    def audio_embedding(self) -> AudioEmbeddingSettings:
        """Get audio embedding settings."""
        if self._audio_embedding is None:
            self._audio_embedding = AudioEmbeddingSettings()
        return self._audio_embedding

    @property
    def text_embedding(self) -> TextEmbeddingSettings:
        """Get text embedding settings."""
        if self._text_embedding is None:
            self._text_embedding = TextEmbeddingSettings()
        return self._text_embedding

    @property
    def metadata_config(self) -> MetadataSettings:
        """Get metadata settings."""
        if self._metadata is None:
            self._metadata = MetadataSettings()
        return self._metadata

    @property
    def storage(self) -> StorageSettings:
        """Get storage settings."""
        if self._storage is None:
            self._storage = StorageSettings()
        return self._storage

    @property
    def pipeline(self) -> PipelineSettings:
        """Get pipeline settings."""
        if self._pipeline is None:
            self._pipeline = PipelineSettings()
        return self._pipeline

    @property
    def clap(self) -> CLAPSettings:
        """Get CLAP-specific settings."""
        if self._clap is None:
            self._clap = CLAPSettings()
        return self._clap

    @property
    def lock(self) -> LockSettings:
        """Get lock settings."""
        if self._lock is None:
            self._lock = LockSettings()
        return self._lock

    @property
    def metrics(self) -> MetricsSettings:
        """Get metrics settings."""
        if self._metrics is None:
            self._metrics = MetricsSettings()
        return self._metrics

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a known level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.env.lower() == "production"

    @property
    def data_dir(self) -> Path:
        """Get the data directory path."""
        path = Path("./data")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_directories(self) -> None:
        """Create all required directories."""
        dirs = [
            self.data_dir,
            Path(self.storage.storage_base_path),
            Path(self.storage.audio_storage_path),
            Path(self.storage.transcript_storage_path),
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    """Factory function to create settings instance.

    Returns:
        Settings: Application settings loaded from environment.
    """
    return Settings()
