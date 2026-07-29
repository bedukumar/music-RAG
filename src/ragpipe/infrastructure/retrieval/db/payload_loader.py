"""Payload loader implementation."""

from typing import Dict, List

from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.retrieval.models import (
    RetrievalResult,
    RetrievedChunk,
    RetrievedMedia,
    SearchResult,
)
from ragpipe.domain.retrieval.ports import PayloadLoader


class PayloadLoaderImpl(PayloadLoader):
    """Hydrates retrieval results using MediaRepository."""

    def __init__(self, media_repository: MediaRepository):
        self.media_repo = media_repository

    async def load_payloads(
        self, results: List[RetrievalResult]
    ) -> List[SearchResult]:
        """Group chunks by media_id and load rich media details."""
        media_chunks: Dict[str, List[RetrievedChunk]] = {}
        
        # We also need the highest score for a media item (usually the top chunk's score)
        media_scores: Dict[str, float] = {}

        for res in results:
            if not res.media_id:
                continue

            chunk = RetrievedChunk(
                chunk_id=res.chunk_id,
                modality=res.modality,
                score=res.score,
                content=res.payload.get("text_content", ""),
                timestamps=res.payload.get("timestamps")
            )

            if res.media_id not in media_chunks:
                media_chunks[res.media_id] = []
                media_scores[res.media_id] = res.score
            
            media_chunks[res.media_id].append(chunk)

        search_results = []
        
        # In a real impl, we might want to batch load the media items
        for media_id, chunks in media_chunks.items():
            # Usually get() is synchronous in the interface but we can run it in executor or it might be patched
            # Looking at MediaRepository, get() is synchronous
            media = await self.media_repo.get(media_id)
            if not media:
                continue
                
            retrieved_media = RetrievedMedia(
                media_id=media.id,
                title=media.metadata_fields.get("title", media.title if media.title else "Unknown Title"),
                media_type=media.media_type.value,
                metadata=media.metadata_fields
            )
            
            search_results.append(
                SearchResult(
                    media=retrieved_media,
                    matched_chunks=chunks,
                    overall_score=media_scores[media_id]
                )
            )

        # Sort search results by the highest chunk score
        search_results.sort(key=lambda x: x.overall_score, reverse=True)
        return search_results
