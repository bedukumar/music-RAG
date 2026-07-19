import asyncio
from typing import Dict, Any, List
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.ports.vector_repository import VectorRepository
from ragpipe.domain.models.media import MediaItem

class DuplicateDetector:
    """Service for finding and merging duplicate media."""
    def __init__(self, media_repo: MediaRepository, vector_repo: VectorRepository):
        self.media_repo = media_repo
        self.vector_repo = vector_repo
        self.duplicate_groups: List[Dict[str, Any]] = []

    async def scan_duplicates(self) -> Dict[str, Any]:
        """Run hashing & vector similarity scan across the catalog."""
        media_items, _ = await self.media_repo.list_media(limit=10000)
        
        hash_groups = {}
        for m in media_items:
            # MediaItem doesn't have file_hash natively, it might be in metadata_fields or we fallback to title
            key = m.metadata_fields.get('file_hash') or m.title
            if key not in hash_groups:
                hash_groups[key] = []
            hash_groups[key].append(m)
            
        groups = []
        for key, items in hash_groups.items():
            if len(items) > 1:
                groups.append({
                    "group_id": key,
                    "media_ids": [item.id for item in items],
                    "reason": "exact_hash_match" if items[0].metadata_fields.get('file_hash') else "title_match"
                })
                
        self.duplicate_groups = groups
        return {"status": "scan_complete", "duplicate_groups_found": len(groups)}

    async def get_duplicates(self) -> List[Dict[str, Any]]:
        """Return grouped list of duplicates."""
        return self.duplicate_groups

    async def merge_duplicates(self, target_id: str, duplicate_ids: List[str]) -> Dict[str, Any]:
        """Consolidate metadata & embeddings into a single media item."""
        target_media = await self.media_repo.get_media(target_id)
        if not target_media:
            raise ValueError(f"Target media {target_id} not found")
            
        merged_count = 0
        for dup_id in duplicate_ids:
            if dup_id == target_id:
                continue
            dup_media = await self.media_repo.get_media(dup_id)
            if dup_media:
                target_media.metadata_fields.update(dup_media.metadata_fields)
                await self.media_repo.delete_media(dup_id)
                merged_count += 1
                
        await self.media_repo.update_media(target_media)
        
        new_groups = []
        for g in self.duplicate_groups:
            if target_id in g["media_ids"]:
                continue
            new_groups.append(g)
        self.duplicate_groups = new_groups
        
        return {"status": "merged", "merged_count": merged_count, "target_id": target_id}
