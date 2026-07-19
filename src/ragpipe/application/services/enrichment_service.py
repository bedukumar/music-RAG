import uuid
import asyncio
from typing import Dict, Any, Optional
from ragpipe.domain.ports.media_repository import MediaRepository

class EnrichmentService:
    """Service for AI metadata enrichment."""
    def __init__(self, media_repo: MediaRepository):
        self.media_repo = media_repo
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.config = {
            "prompt": "Extract topics and sentiment",
            "max_tokens": 1024,
            "model": "gpt-3.5-turbo"
        }

    async def start_enrichment(self, media_id: str) -> str:
        media = await self.media_repo.get_media(media_id)
        if not media:
            raise ValueError(f"Media not found: {media_id}")
            
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = {
            "job_id": job_id,
            "media_id": media_id,
            "status": "pending",
            "result": None
        }
        
        asyncio.create_task(self._mock_enrichment_task(job_id, media_id))
        return job_id

    async def _mock_enrichment_task(self, job_id: str, media_id: str):
        self.jobs[job_id]["status"] = "processing"
        # Mock delay
        await asyncio.sleep(2)
        
        result = {
            "sentiment": "positive",
            "summary": "This is a great piece of content.",
            "tags": ["informative", "educational"]
        }
        
        try:
            media = await self.media_repo.get_media(media_id)
            if media:
                if "enrichment" not in media.metadata:
                    media.metadata["enrichment"] = {}
                media.metadata["enrichment"].update(result)
                await self.media_repo.update_media(media)
        except Exception:
            pass
            
        self.jobs[job_id]["status"] = "completed"
        self.jobs[job_id]["result"] = result

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> list:
        return list(self.jobs.values())

    def update_config(self, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in config_updates.items():
            if k in self.config:
                self.config[k] = v
        return self.config
