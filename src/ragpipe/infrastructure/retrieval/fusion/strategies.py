"""Result fusion strategies."""

from typing import Dict, List

from ragpipe.domain.models.modality import Modality
from ragpipe.domain.retrieval.models import RetrievalResult
from ragpipe.domain.retrieval.ports import FusionStrategy


class ReciprocalRankFusion(FusionStrategy):
    """Fuses multiple ranked lists using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self, modality_results: Dict[Modality, List[RetrievalResult]], top_k: int
    ) -> List[RetrievalResult]:
        """Fuses results using RRF score = 1 / (k + rank)."""
        score_map = {}
        result_map = {}

        for modality, results in modality_results.items():
            for rank, result in enumerate(results, start=1):
                chunk_id = result.chunk_id
                if chunk_id not in score_map:
                    score_map[chunk_id] = 0.0
                    result_map[chunk_id] = result
                
                score_map[chunk_id] += 1.0 / (self.k + rank)

        # Sort by accumulated RRF score
        fused = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        
        final_results = []
        for chunk_id, score in fused[:top_k]:
            # Update the score with the fusion score
            res = result_map[chunk_id]
            final_results.append(
                RetrievalResult(
                    modality=res.modality,
                    chunk_id=res.chunk_id,
                    media_id=res.media_id,
                    score=score,
                    payload=res.payload
                )
            )

        return final_results


class WeightedFusionStrategy(FusionStrategy):
    """Fuses results using a weighted linear combination of scores."""

    def __init__(self, weights: Dict[Modality, float]):
        self.weights = weights

    def fuse(
        self, modality_results: Dict[Modality, List[RetrievalResult]], top_k: int
    ) -> List[RetrievalResult]:
        """Fuses results using weights."""
        score_map = {}
        result_map = {}

        for modality, results in modality_results.items():
            weight = self.weights.get(modality, 1.0)
            for result in results:
                chunk_id = result.chunk_id
                if chunk_id not in score_map:
                    score_map[chunk_id] = 0.0
                    result_map[chunk_id] = result
                
                score_map[chunk_id] += result.score * weight

        fused = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        
        final_results = []
        for chunk_id, score in fused[:top_k]:
            res = result_map[chunk_id]
            final_results.append(
                RetrievalResult(
                    modality=res.modality,
                    chunk_id=res.chunk_id,
                    media_id=res.media_id,
                    score=score,
                    payload=res.payload
                )
            )

        return final_results
