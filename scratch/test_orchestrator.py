import asyncio
import os
import sys

from ragpipe.container import Container
from ragpipe.domain.models.media import Song, MediaType

async def test():
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///ragpipe.db")
    storage_path = os.getenv("STORAGE_PATH", "./data")
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

    container = Container(db_url=db_url, storage_path=storage_path, qdrant_url=qdrant_url)
    await container.init_resources()

    try:
        # Create a new media item with a source_url
        song = Song.create(
            title="Test Song URL",
            source_url="https://example.com/audio.mp3"
        )
        
        # Register it using the new MediaRegistrar
        saved_media = await container.media_registrar.register_media(song)
        print(f"Registered Media: {saved_media.id}")

        # Check modalities saved in DB
        statuses = await container.media_repository.list_modality_statuses(saved_media.id)
        for s in statuses:
            print(f"- {s.modality.value}: data_available={s.data_available}, status={s.embedding_status}")

        # Trigger Orchestrator
        print("Running Orchestrator...")
        jobs = await container.pipeline_orchestrator.process_media(saved_media.id)
        
        print("Jobs created:")
        for j in jobs:
            print(f"- {j.modality.value}: Job ID {j.id}")

    finally:
        await container.close_resources()

if __name__ == "__main__":
    asyncio.run(test())
