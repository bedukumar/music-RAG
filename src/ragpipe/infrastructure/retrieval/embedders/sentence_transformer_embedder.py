"""SentenceTransformer query embedder for transcript retrieval."""

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import QueryEmbedding
from ragpipe.domain.retrieval.ports import QueryEmbedder
from ragpipe.infrastructure.embedders.sentence_transformer import (
    SentenceTransformerEmbedder,
)


class SentenceTransformerQueryEmbedder(QueryEmbedder):
    """Adapter for standard text embedding."""

    def __init__(self, text_provider: SentenceTransformerEmbedder):
        self.provider = text_provider

    async def embed_query(self, query: str) -> QueryEmbedding:
        """Embeds text into vector space."""
        vector = await self.provider.embed_text(query)
        return QueryEmbedding(modality=Modality.TRANSCRIPT, vector=vector.flatten().tolist())

    @property
    def modality(self) -> Modality:
        return Modality.TRANSCRIPT
