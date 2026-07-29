"""Qdrant metadata retriever implementation."""

import asyncio

from qdrant_client import QdrantClient
from qdrant_client.http import models

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import RetrievalResult, SearchQuery
from ragpipe.domain.retrieval.ports import MetadataRetriever


class QdrantMetadataRetriever(MetadataRetriever):
    """Adapter for retrieving via metadata filters from Qdrant payloads."""

    def __init__(self, qdrant_client: QdrantClient, collection_name: str):
        self.client = qdrant_client
        self.collection_name = collection_name

    async def search(
        self, query: SearchQuery, top_k: int
    ) -> list[RetrievalResult]:
        """Search the metadata payloads in Qdrant using Qdrant scroll/search API."""
        # Build Qdrant filter based on SearchQuery filters
        must_conditions = []
        for key, val in query.filters.exact_matches.items():
            must_conditions.append(
                models.FieldCondition(
                    key=key, match=models.MatchValue(value=val)
                )
            )

        if query.filters.tag_matches:
            for tag in query.filters.tag_matches:
                must_conditions.append(
                    models.FieldCondition(
                        key="tags", match=models.MatchValue(value=tag)
                    )
                )

        qdrant_filter = models.Filter(must=must_conditions) if must_conditions else None

        def sync_scroll():
            # If there's text, we would ideally do a keyword search, but without a vector
            # we just scroll or filter by the exact matches.
            res, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_filter,
                limit=top_k,
                with_payload=True
            )
            return res

        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(None, sync_scroll)

        results = []
        for rec in records:
            payload = rec.payload or {}
            results.append(
                RetrievalResult(
                    modality=Modality.METADATA,
                    chunk_id=str(rec.id),
                    media_id=payload.get("media_id", ""),
                    score=1.0,  # Exact matches get a 1.0 score
                    payload=payload
                )
            )

        return results
