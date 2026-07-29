"""CLAP query embedder for audio retrieval."""

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import QueryEmbedding
from ragpipe.domain.retrieval.ports import QueryEmbedder
from ragpipe.infrastructure.embedders.clap_embedder import CLAPEmbedder


class CLAPQueryEmbedder(QueryEmbedder):
    """Adapter for CLAP text-to-audio embedding."""

    def __init__(self, clap_provider: CLAPEmbedder):
        self.provider = clap_provider

    async def embed_query(self, query: str) -> QueryEmbedding:
        """Embeds text into the shared CLAP audio space."""
        # Using the real CLAP model's text encoder
        vector = await self.provider.embed_text(query)
        # Convert (1, 512) numpy array to flat list
        return QueryEmbedding(modality=Modality.AUDIO, vector=vector.flatten().tolist())

    @property
    def modality(self) -> Modality:
        return Modality.AUDIO
