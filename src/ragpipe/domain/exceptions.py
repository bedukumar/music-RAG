"""Domain exceptions for the RAG Data Ingestion Platform.

This module defines a hierarchy of domain-specific exceptions that provide
structured error context for observability, logging, and error handling
throughout the platform.
"""

from __future__ import annotations


class RagPipeError(Exception):
    """Base exception for all RAG pipeline errors.

    All domain exceptions inherit from this class, allowing callers to
    catch any platform error with a single except clause when appropriate.
    """

    def __init__(self, message: str) -> None:
        """Initialise the base error.

        Args:
            message: Human-readable error description.
        """
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


class MediaNotFoundError(RagPipeError):
    """Raised when a media item cannot be found by its identifier."""

    def __init__(self, media_id: str, message: str | None = None) -> None:
        """Initialise the error.

        Args:
            media_id: The identifier of the media item that was not found.
            message: Optional override message.
        """
        self.media_id = media_id
        super().__init__(message or f"Media item not found: {media_id}")


class DuplicateMediaError(RagPipeError):
    """Raised when attempting to create a media item that already exists."""

    def __init__(self, media_id: str, message: str | None = None) -> None:
        """Initialise the error.

        Args:
            media_id: The identifier of the duplicate media item.
            message: Optional override message.
        """
        self.media_id = media_id
        super().__init__(message or f"Media item already exists: {media_id}")


class InvalidMediaError(RagPipeError):
    """Raised when media data fails validation."""

    def __init__(self, details: str, message: str | None = None) -> None:
        """Initialise the error.

        Args:
            details: Specific validation failure details.
            message: Optional override message.
        """
        self.details = details
        super().__init__(message or f"Invalid media: {details}")


class PipelineError(RagPipeError):
    """Raised when a processing pipeline stage fails."""

    def __init__(
        self,
        media_id: str,
        modality: str,
        stage: str,
        details: str,
        message: str | None = None,
    ) -> None:
        """Initialise the error.

        Args:
            media_id: The media item being processed.
            modality: The modality being processed (audio, transcript, metadata).
            stage: The pipeline stage that failed.
            details: Detailed failure information.
            message: Optional override message.
        """
        self.media_id = media_id
        self.modality = modality
        self.stage = stage
        self.details = details
        super().__init__(
            message
            or f"Pipeline error for media={media_id} modality={modality} "
            f"stage={stage}: {details}"
        )


class EmbeddingError(RagPipeError):
    """Raised when embedding generation or retrieval fails."""

    def __init__(
        self, model_name: str, details: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            model_name: The embedding model that encountered the error.
            details: Detailed failure information.
            message: Optional override message.
        """
        self.model_name = model_name
        self.details = details
        super().__init__(
            message or f"Embedding error with model={model_name}: {details}"
        )


class ChunkingError(RagPipeError):
    """Raised when content chunking fails."""

    def __init__(
        self, strategy: str, details: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            strategy: The chunking strategy that failed.
            details: Detailed failure information.
            message: Optional override message.
        """
        self.strategy = strategy
        self.details = details
        super().__init__(
            message or f"Chunking error with strategy={strategy}: {details}"
        )


class VectorStoreError(RagPipeError):
    """Raised when vector database operations fail."""

    def __init__(
        self, operation: str, details: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            operation: The vector store operation that failed.
            details: Detailed failure information.
            message: Optional override message.
        """
        self.operation = operation
        self.details = details
        super().__init__(
            message
            or f"Vector store error during operation={operation}: {details}"
        )


class MigrationError(RagPipeError):
    """Raised when an index migration fails."""

    def __init__(
        self, migration_id: str, details: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            migration_id: The identifier of the migration that failed.
            details: Detailed failure information.
            message: Optional override message.
        """
        self.migration_id = migration_id
        self.details = details
        super().__init__(
            message
            or f"Migration error for migration={migration_id}: {details}"
        )


class LockError(RagPipeError):
    """Raised when a distributed lock operation fails."""

    def __init__(
        self, resource_id: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            resource_id: The resource whose lock operation failed.
            message: Optional override message.
        """
        self.resource_id = resource_id
        super().__init__(
            message or f"Lock error for resource={resource_id}"
        )


class ConfigurationError(RagPipeError):
    """Raised when a configuration parameter is invalid or missing."""

    def __init__(
        self, parameter: str, details: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            parameter: The configuration parameter that is problematic.
            details: Detailed failure information.
            message: Optional override message.
        """
        self.parameter = parameter
        self.details = details
        super().__init__(
            message
            or f"Configuration error for parameter={parameter}: {details}"
        )


class ValidationError(RagPipeError):
    """Raised when a domain value fails validation constraints."""

    def __init__(
        self, field: str, details: str, message: str | None = None
    ) -> None:
        """Initialise the error.

        Args:
            field: The field that failed validation.
            details: Detailed validation failure information.
            message: Optional override message.
        """
        self.field = field
        self.details = details
        super().__init__(
            message or f"Validation error on field={field}: {details}"
        )
