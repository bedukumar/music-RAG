"""
Media API Routes.
"""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File, BackgroundTasks

from ragpipe.domain.exceptions import MediaNotFoundError
from ragpipe.domain.models.media import MediaItem, MediaType, Song, Podcast, Video
from ragpipe.domain.models.modality import Modality
from ragpipe.interfaces.schemas.media_schemas import (
    MediaCreateRequest,
    MediaListResponse,
    MediaResponse,
    MediaUpdateRequest,
)
from ragpipe.interfaces.schemas.pipeline_schemas import ProcessRequest

router = APIRouter(prefix="/media", tags=["media"])


def get_registrar(request: Request):
    return request.app.state.container.media_registrar


def get_orchestrator(request: Request):
    return request.app.state.container.pipeline_orchestrator


def get_media_repo(request: Request):
    return request.app.state.container.media_repository


@router.post("", response_model=MediaResponse)
async def create_media(
    req: MediaCreateRequest,
    background_tasks: BackgroundTasks,
    registrar=Depends(get_registrar),
    orchestrator=Depends(get_orchestrator)
):
    """Create a new media item."""
    try:
        media_type = MediaType(req.media_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid media type: {req.media_type}")
        
    if media_type == MediaType.SONG:
        media = Song.create(
            title=req.title, artist=req.artist, album=req.album,
            genre=req.genre, tags=req.tags or [], duration=req.duration,
            language=req.language, source_url=req.source_url,
            audio_path=req.audio_path, transcript_text=req.transcript_text,
            metadata_fields=req.metadata_fields or {},
            lyrics=req.lyrics, bpm=req.bpm, key=req.musical_key
        )
    elif media_type == MediaType.PODCAST:
        media = Podcast.create(
            title=req.title, artist=req.artist, album=req.album,
            genre=req.genre, tags=req.tags or [], duration=req.duration,
            language=req.language, source_url=req.source_url,
            audio_path=req.audio_path, transcript_text=req.transcript_text,
            metadata_fields=req.metadata_fields or {},
            show_name=req.show_name, episode_number=req.episode_number,
            host=req.host, guests=req.guests or []
        )
    else:
        media = Video.create(
            title=req.title, artist=req.artist, album=req.album,
            genre=req.genre, tags=req.tags or [], duration=req.duration,
            language=req.language, source_url=req.source_url,
            audio_path=req.audio_path, transcript_text=req.transcript_text,
            metadata_fields=req.metadata_fields or {},
            resolution=req.resolution, fps=req.fps, video_path=req.video_path
        )
        
    saved_media = await registrar.register_media(media)
    return saved_media


@router.get("", response_model=MediaListResponse)
async def list_media(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    media_type: Optional[str] = None,
    media_repo=Depends(get_media_repo)
):
    """List media items."""
    filters = {}
    if media_type:
        filters["media_type"] = media_type
        
    items, total = await media_repo.list_all(offset=offset, limit=limit, **filters)
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(media_id: str, media_repo=Depends(get_media_repo)):
    """Get a specific media item."""
    media = await media_repo.get(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    statuses = await media_repo.list_modality_statuses(media_id)
    # We create a dictionary to match the expected pydantic response if needed,
    # or just rely on from_attributes
    
    # Need to manually attach statuses for the response model
    media_dict = vars(media).copy()
    media_dict["media_type"] = media.media_type.value
    media_dict["modality_statuses"] = [
        {
            "modality": s.modality.value,
            "data_available": s.data_available,
            "embedding_status": s.embedding_status,
            "last_processed": s.last_processed,
            "error_message": s.error_message
        } for s in statuses
    ]
    return media_dict


@router.put("/{media_id}")
async def update_media(
    media_id: str,
    req: MediaUpdateRequest,
    registrar=Depends(get_registrar)
):
    """Update a media item."""
    # Simplified: in a real system we'd handle full updates, 
    # but here we rely on the specific endpoints below for data updates
    pass


@router.delete("/{media_id}")
async def delete_media(media_id: str, registrar=Depends(get_registrar)):
    """Delete a media item."""
    try:
        await registrar.delete_media(media_id)
        return {"status": "deleted"}
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail="Media not found")


@router.post("/{media_id}/audio")
async def update_audio(
    media_id: str,
    audio_path: str,
    duration: Optional[float] = None,
    registrar=Depends(get_registrar)
):
    """Update audio path."""
    try:
        await registrar.update_audio(media_id, audio_path, duration)
        return {"status": "updated"}
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail="Media not found")


@router.post("/{media_id}/transcript")
async def update_transcript(
    media_id: str,
    transcript: str,
    registrar=Depends(get_registrar)
):
    """Update transcript text."""
    try:
        await registrar.update_transcript(media_id, transcript)
        return {"status": "updated"}
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail="Media not found")


@router.put("/{media_id}/metadata")
async def update_metadata(
    media_id: str,
    metadata: dict,
    registrar=Depends(get_registrar)
):
    """Update metadata fields."""
    try:
        await registrar.update_metadata(media_id, metadata)
        return {"status": "updated"}
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail="Media not found")


@router.post("/{media_id}/process")
async def process_media(
    media_id: str,
    req: ProcessRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    orchestrator=Depends(get_orchestrator)
):
    """Trigger processing for media."""
    try:
        modalities = None
        if req.modalities:
            modalities = [Modality(m) for m in req.modalities]
            
        jobs = await orchestrator.process_media(media_id, modalities)
        
        for job in jobs:
            async def run_job(j=job):
                try:
                    await orchestrator.execute_job(j)
                finally:
                    try:
                        await request.app.state.container._shared_session.remove()
                    except Exception:
                        pass
            background_tasks.add_task(run_job)
            
        return {"jobs_created": len(jobs), "job_ids": [j.id for j in jobs]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{media_id}/reprocess/{modality}")
async def reprocess_modality(
    media_id: str,
    modality: str,
    request: Request,
    background_tasks: BackgroundTasks,
    orchestrator=Depends(get_orchestrator)
):
    """Force reprocess a specific modality."""
    try:
        mod = Modality(modality)
        job = await orchestrator.reprocess_modality(media_id, mod)
        
        async def run_job(j=job):
            try:
                await orchestrator.execute_job(j)
            finally:
                try:
                    await request.app.state.container._shared_session.remove()
                except Exception:
                    pass
                    
        background_tasks.add_task(run_job)
        return {"job_id": job.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/upload")
async def upload_media_file(
    request: Request,
    file: UploadFile = File(...)
):
    """Upload a media file and return its absolute path."""
    file_storage = request.app.state.container.file_storage
    data = await file.read()
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    filename = f"{uuid.uuid4()}{ext}"
    saved_path = await file_storage.save(f"uploads/{filename}", data)
    
    full_path = file_storage._get_full_path(saved_path)
    return {"path": str(full_path)}

