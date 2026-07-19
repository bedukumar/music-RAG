from fastapi import APIRouter, Depends, HTTPException, Request
from ragpipe.domain.ports.file_storage import FileStorage
from ragpipe.domain.ports.media_repository import MediaRepository
from ragpipe.domain.models.modality import Modality

router = APIRouter(prefix="/storage", tags=["storage"])

def get_file_storage(request: Request) -> FileStorage:
    # Actually container has 'file_storage' if initialized
    # Let's check container.py - wait, it is created in container.py as self.file_storage
    return request.app.state.container.file_storage

def get_media_repo(request: Request) -> MediaRepository:
    return request.app.state.container.media_repository

@router.get("/usage")
async def get_storage_usage(
    file_storage: FileStorage = Depends(get_file_storage),
    media_repo: MediaRepository = Depends(get_media_repo)
):
    """Breakdown of bytes across modalities."""
    usage = {
        "audio": 0,
        "video": 0,
        "transcript": 0,
        "image": 0,
        "total": 0
    }
    
    try:
        all_files = await file_storage.list_files("")
        for f in all_files:
            size = await file_storage.get_file_size(f)
            usage["total"] += size
            ext = f.split(".")[-1].lower() if "." in f else ""
            if ext in ["mp3", "wav", "flac"]:
                usage["audio"] += size
            elif ext in ["mp4", "mkv", "avi"]:
                usage["video"] += size
            elif ext in ["jpg", "jpeg", "png"]:
                usage["image"] += size
            elif ext in ["txt", "srt", "vtt", "json"]:
                usage["transcript"] += size
    except Exception:
        pass # Fallback to 0s
        
    return usage

@router.post("/cleanup")
async def cleanup_storage(
    file_storage: FileStorage = Depends(get_file_storage),
    media_repo: MediaRepository = Depends(get_media_repo)
):
    """Removes unreferenced audio/video/image files."""
    media_items, _ = await media_repo.list_media(limit=10000)
    referenced_paths = set()
    for m in media_items:
        if m.audio_path:
            referenced_paths.add(m.audio_path)
        if hasattr(m, "video_path") and m.video_path:
            referenced_paths.add(m.video_path)
            
    all_files = await file_storage.list_files("")
    removed = 0
    bytes_freed = 0
    for f in all_files:
        if f not in referenced_paths:
            size = await file_storage.get_file_size(f)
            await file_storage.delete(f)
            removed += 1
            bytes_freed += size
            
    return {"status": "cleanup_complete", "files_removed": removed, "bytes_freed": bytes_freed}

@router.delete("/media/{media_id}/files")
async def delete_media_files(
    media_id: str,
    file_storage: FileStorage = Depends(get_file_storage),
    media_repo: MediaRepository = Depends(get_media_repo)
):
    """Nukes specific raw files."""
    media = await media_repo.get_media(media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
        
    deleted = []
    if media.audio_path:
        await file_storage.delete(media.audio_path)
        deleted.append(media.audio_path)
        
    if hasattr(media, "video_path") and media.video_path:
        await file_storage.delete(media.video_path)
        deleted.append(media.video_path)
        
    return {"status": "files_deleted", "deleted_files": deleted}

@router.get("/config")
async def get_storage_config():
    """Configuration for Max Storage."""
    return {
        "max_storage_bytes": 100 * 1024 * 1024 * 1024, # 100 GB
        "retention_policy": "keep_forever",
        "auto_cleanup": False
    }
