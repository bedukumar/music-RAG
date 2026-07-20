"""
Media API Routes.
"""

import os
import uuid
import html
import re
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
    BatchCreateRequest,
    BatchProcessRequest,
    BatchDeleteRequest,
    BatchOperationResponse
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
        
    safe_transcript = sanitize_text(req.transcript_text) if req.transcript_text else None
    safe_metadata = sanitize_metadata(req.metadata_fields) if req.metadata_fields else {}
    
    if media_type == MediaType.SONG:
        media = Song.create(
            title=html.escape(req.title), artist=html.escape(req.artist) if req.artist else None, album=html.escape(req.album) if req.album else None,
            genre=req.genre, tags=[html.escape(t) for t in req.tags] if req.tags else [], duration=req.duration,
            language=req.language, source_url=req.source_url,
            audio_path=req.audio_path, transcript_text=safe_transcript,
            metadata_fields=safe_metadata,
            lyrics=sanitize_text(req.lyrics) if req.lyrics else None, bpm=req.bpm, key=req.musical_key
        )
    elif media_type == MediaType.PODCAST:
        media = Podcast.create(
            title=html.escape(req.title), artist=html.escape(req.artist) if req.artist else None, album=html.escape(req.album) if req.album else None,
            genre=req.genre, tags=[html.escape(t) for t in req.tags] if req.tags else [], duration=req.duration,
            language=req.language, source_url=req.source_url,
            audio_path=req.audio_path, transcript_text=safe_transcript,
            metadata_fields=safe_metadata,
            show_name=html.escape(req.show_name) if req.show_name else None, episode_number=req.episode_number,
            host=html.escape(req.host) if req.host else None, guests=[html.escape(g) for g in req.guests] if req.guests else []
        )
    else:
        media = Video.create(
            title=html.escape(req.title), artist=html.escape(req.artist) if req.artist else None, album=html.escape(req.album) if req.album else None,
            genre=req.genre, tags=[html.escape(t) for t in req.tags] if req.tags else [], duration=req.duration,
            language=req.language, source_url=req.source_url,
            audio_path=req.audio_path, transcript_text=safe_transcript,
            metadata_fields=safe_metadata,
            resolution=req.resolution, fps=req.fps, video_path=req.video_path
        )
        
    saved_media = await registrar.register_media(media)
    return saved_media


@router.post("/batch", response_model=BatchOperationResponse)
async def create_media_batch(
    req: BatchCreateRequest,
    registrar=Depends(get_registrar)
):
    """Create multiple media items in batch."""
    media_items = []
    failed = {}
    
    for item_req in req.items:
        try:
            media_type = MediaType(item_req.media_type.lower())
            safe_transcript = sanitize_text(item_req.transcript_text) if item_req.transcript_text else None
            safe_metadata = sanitize_metadata(item_req.metadata_fields) if item_req.metadata_fields else {}
            
            if media_type == MediaType.SONG:
                media = Song.create(
                    title=html.escape(item_req.title), artist=html.escape(item_req.artist) if item_req.artist else None, album=html.escape(item_req.album) if item_req.album else None,
                    genre=item_req.genre, tags=[html.escape(t) for t in item_req.tags] if item_req.tags else [], duration=item_req.duration,
                    language=item_req.language, source_url=item_req.source_url,
                    audio_path=item_req.audio_path, transcript_text=safe_transcript,
                    metadata_fields=safe_metadata,
                    lyrics=sanitize_text(item_req.lyrics) if item_req.lyrics else None, bpm=item_req.bpm, key=item_req.musical_key
                )
            elif media_type == MediaType.PODCAST:
                media = Podcast.create(
                    title=html.escape(item_req.title), artist=html.escape(item_req.artist) if item_req.artist else None, album=html.escape(item_req.album) if item_req.album else None,
                    genre=item_req.genre, tags=[html.escape(t) for t in item_req.tags] if item_req.tags else [], duration=item_req.duration,
                    language=item_req.language, source_url=item_req.source_url,
                    audio_path=item_req.audio_path, transcript_text=safe_transcript,
                    metadata_fields=safe_metadata,
                    show_name=html.escape(item_req.show_name) if item_req.show_name else None, episode_number=item_req.episode_number,
                    host=html.escape(item_req.host) if item_req.host else None, guests=[html.escape(g) for g in item_req.guests] if item_req.guests else []
                )
            else:
                media = Video.create(
                    title=html.escape(item_req.title), artist=html.escape(item_req.artist) if item_req.artist else None, album=html.escape(item_req.album) if item_req.album else None,
                    genre=item_req.genre, tags=[html.escape(t) for t in item_req.tags] if item_req.tags else [], duration=item_req.duration,
                    language=item_req.language, source_url=item_req.source_url,
                    audio_path=item_req.audio_path, transcript_text=safe_transcript,
                    metadata_fields=safe_metadata,
                    resolution=item_req.resolution, fps=item_req.fps, video_path=item_req.video_path
                )
            media_items.append(media)
        except Exception as e:
            failed[item_req.title] = f"Validation error: {str(e)}"
            
    successful, registrar_failed = await registrar.register_batch(media_items)
    failed.update(registrar_failed)
    
    return BatchOperationResponse(
        successful=successful,
        failed=failed,
        skipped=[]
    )


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
    
    # Attach modality_statuses to each item
    items_with_statuses = []
    for item in items:
        statuses = await media_repo.list_modality_statuses(item.id)
        item_dict = vars(item).copy()
        item_dict["media_type"] = item.media_type.value
        item_dict["modality_statuses"] = [
            {
                "modality": s.modality.value,
                "data_available": s.data_available,
                "embedding_status": s.embedding_status,
                "last_processed": s.last_processed,
                "error_message": s.error_message
            } for s in statuses
        ]
        items_with_statuses.append(item_dict)
        
    return {"items": items_with_statuses, "total": total, "offset": offset, "limit": limit}


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


@router.delete("/batch", response_model=BatchOperationResponse)
async def delete_media_batch(
    req: BatchDeleteRequest,
    registrar=Depends(get_registrar)
):
    """Delete multiple media items."""
    if req.dry_run:
        return BatchOperationResponse(successful=req.media_ids, failed={}, skipped=[])
        
    successful, failed = await registrar.delete_batch(req.media_ids)
    return BatchOperationResponse(successful=successful, failed=failed, skipped=[])


def sanitize_text(text: str, max_length: int = 500000) -> str:
    """Basic sanitization: strip and escape HTML, enforce max length."""
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        raise HTTPException(status_code=400, detail=f"Text exceeds max length of {max_length}")
    # Escape HTML to prevent XSS
    return html.escape(text)

def sanitize_metadata(metadata: dict) -> dict:
    """Ensure metadata contains only safe strings and basic types."""
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=400, detail="Metadata must be a dictionary")
        
    sanitized = {}
    for k, v in metadata.items():
        safe_key = html.escape(str(k).strip())
        if len(safe_key) > 255:
            continue
            
        if isinstance(v, str):
            sanitized[safe_key] = html.escape(v.strip())[:10000] # Limit string length
        elif isinstance(v, (int, float, bool, type(None))):
            sanitized[safe_key] = v
        elif isinstance(v, list):
            safe_list = []
            for item in v:
                if isinstance(item, str):
                    safe_list.append(html.escape(item.strip())[:10000])
                elif isinstance(item, (int, float, bool)):
                    safe_list.append(item)
            sanitized[safe_key] = safe_list
        else:
            sanitized[safe_key] = html.escape(str(v).strip())[:10000]
            
    return sanitized

@router.post("/{media_id}/audio")
async def update_audio(
    media_id: str,
    audio_path: str,
    duration: Optional[float] = None,
    registrar=Depends(get_registrar)
):
    """Update audio path."""
    if not audio_path or len(audio_path) > 2048:
        raise HTTPException(status_code=400, detail="Invalid audio path length")
    if duration is not None and (duration < 0 or duration > 360000): # Max 100 hours
        raise HTTPException(status_code=400, detail="Invalid duration")
        
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
    safe_transcript = sanitize_text(transcript)
    try:
        await registrar.update_transcript(media_id, safe_transcript)
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
    safe_metadata = sanitize_metadata(metadata)
    try:
        await registrar.update_metadata(media_id, safe_metadata)
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


@router.post("/batch/process", response_model=BatchOperationResponse)
async def process_media_batch(
    req: BatchProcessRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    orchestrator=Depends(get_orchestrator)
):
    """Trigger processing for multiple media items."""
    successful = []
    failed = {}
    
    modalities = None
    if req.modalities:
        try:
            modalities = [Modality(m) for m in req.modalities]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
    for media_id in req.media_ids:
        try:
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
            successful.append(media_id)
        except Exception as e:
            failed[media_id] = str(e)
            
    return BatchOperationResponse(successful=successful, failed=failed, skipped=[])


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

