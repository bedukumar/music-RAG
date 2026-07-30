"""Application facade for media lookup and retrieval-backed searches."""

from __future__ import annotations

from typing import Any, Optional

from ragpipe.application.retrieval.services.search_service import SearchService as RetrievalSearchService
from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import SearchFilters, SearchQuery
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.application.services.status_service import StatusService


class MediaQueryService:
    """Expose media lookup helpers for chat tools."""

    def __init__(
        self,
        media_repository: MediaRepository,
        status_service: StatusService,
        retrieval_search_service: RetrievalSearchService,
    ) -> None:
        self.media_repo = media_repository
        self.status_service = status_service
        self.retrieval_search_service = retrieval_search_service

    async def get_media_details(self, media_id: str) -> dict[str, Any]:
        media = await self.media_repo.get(media_id)
        if not media:
            return {}

        statuses = await self.media_repo.list_modality_statuses(media_id)
        pipeline_status = await self.status_service.get_pipeline_status(media_id)
        return {
            "media": self._serialize_media_item(media),
            "modality_statuses": [
                {
                    "modality": status.modality.value,
                    "data_available": status.data_available,
                    "embedding_status": status.embedding_status,
                    "embedding_version_id": status.embedding_version_id,
                    "last_processed": status.last_processed.isoformat() if status.last_processed else None,
                    "error_message": status.error_message,
                }
                for status in statuses
            ],
            "pipeline_status": pipeline_status,
        }

    async def search_media(
        self,
        *,
        offset: int = 0,
        limit: int = 10,
        media_type: Optional[str] = None,
        filters: Optional[dict[str, object]] = None,
    ) -> dict[str, Any]:
        items, total = await self.media_repo.list_all(
            offset=offset,
            limit=limit,
            media_type=media_type,
            filters=filters,
        )
        return {
            "items": [
                self._serialize_media_item(item)
                for item in items
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    async def search_by_artist(
        self,
        artist: str,
        *,
        top_k: int = 10,
        score_threshold: float = 0.0,
        modalities: Optional[list[Modality]] = None,
    ) -> dict[str, Any]:
        query = SearchQuery(
            text=artist,
            active_modalities=modalities or [Modality.METADATA, Modality.TRANSCRIPT],
            filters=SearchFilters(exact_matches={"artist": artist}),
            top_k=top_k,
            score_threshold=score_threshold,
            rerank=False,
            fusion_strategy="rrf",
        )
        session = await self.retrieval_search_service.search(query)
        return self._serialize_session(session)

    async def search_by_genre(
        self,
        genre: str,
        *,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> dict[str, Any]:
        query = SearchQuery(
            text=genre,
            active_modalities=[Modality.METADATA, Modality.TRANSCRIPT],
            filters=SearchFilters(exact_matches={"genre": genre}),
            top_k=top_k,
            score_threshold=score_threshold,
            rerank=False,
            fusion_strategy="rrf",
        )
        session = await self.retrieval_search_service.search(query)
        return self._serialize_session(session)

    async def search_by_year(
        self,
        year: str,
        *,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> dict[str, Any]:
        items, _ = await self.media_repo.list_all(limit=1000)
        matches = []
        for item in items:
            metadata = getattr(item, "metadata_fields", {}) or {}
            item_years = {
                str(metadata.get("year", "")),
                str(metadata.get("release_year", "")),
                str(metadata.get("date", ""))[:4],
                str(getattr(item.created_at, "year", "")),
            }
            if year in item_years or year in (item.title or "") or year in (item.album or ""):
                matches.append(self._serialize_media_item(item))
        return {
            "session_id": f"year-{year}",
            "results": matches[:top_k],
            "latency_ms": {"total": 0.0},
        }

    def _serialize_session(self, session) -> dict[str, Any]:
        """Convert retrieval dataclasses into JSON-friendly dicts."""

        return {
            "session_id": session.session_id,
            "results": [
                {
                    "media": {
                        "media_id": result.media.media_id,
                        "title": result.media.title,
                        "media_type": result.media.media_type.value
                        if hasattr(result.media.media_type, "value")
                        else result.media.media_type,
                        "metadata": result.media.metadata,
                    },
                    "matched_chunks": [
                        {
                            "chunk_id": chunk.chunk_id,
                            "modality": chunk.modality.value,
                            "score": chunk.score,
                            "content": chunk.content,
                            "timestamps": chunk.timestamps,
                        }
                        for chunk in result.matched_chunks
                    ],
                    "overall_score": result.overall_score,
                }
                for result in session.results
            ],
            "latency_ms": session.latency_ms,
        }

    def _serialize_media_item(self, item) -> dict[str, Any]:
        """Convert domain media objects into JSON-safe dictionaries."""

        payload = {
            "id": item.id,
            "media_type": item.media_type.value if hasattr(item.media_type, "value") else item.media_type,
            "title": item.title,
            "artist": item.artist,
            "album": item.album,
            "genre": item.genre,
            "tags": list(item.tags or []),
            "duration": item.duration,
            "language": item.language,
            "source_url": item.source_url,
            "audio_path": item.audio_path,
            "transcript_text": item.transcript_text,
            "metadata_fields": item.metadata_fields,
            "created_at": item.created_at.isoformat() if hasattr(item.created_at, "isoformat") else item.created_at,
            "updated_at": item.updated_at.isoformat() if hasattr(item.updated_at, "isoformat") else item.updated_at,
        }
        for attr in ("lyrics", "bpm", "key", "show_name", "episode_number", "host", "guests", "description", "resolution", "fps", "video_path"):
            if hasattr(item, attr):
                value = getattr(item, attr)
                if attr == "guests" and value is not None:
                    payload[attr] = list(value)
                else:
                    payload[attr] = value
        return payload
