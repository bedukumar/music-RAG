"""
Embedding Providers.

Implementations of the EmbeddingProvider ports for various models.
"""

from ragpipe.infrastructure.embedders.clap_embedder import CLAPEmbedder
from ragpipe.infrastructure.embedders.mock_embedder import MockAudioEmbedder, MockTextEmbedder
from ragpipe.infrastructure.embedders.sentence_transformer import SentenceTransformerEmbedder

__all__ = [
    "CLAPEmbedder",
    "SentenceTransformerEmbedder",
    "MockAudioEmbedder",
    "MockTextEmbedder",
]
