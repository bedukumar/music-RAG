import os
import sqlite3
from pathlib import Path

import pytest
from ragpipe.application.services.media_registrar import run_batch

@pytest.fixture(scope="function")
def temp_db(tmp_path: Path):
    db_path = tmp_path / "test_ragpipe.db"
    # Ensure the file exists (SQLite will create on connect)
    db_path.touch()
    return db_path

@pytest.mark.asyncio
async def test_batch_ingestion_success(temp_db, tmp_path: Path):
    # Prepare sample CSV
    csv_path = tmp_path / "sample_batch.csv"
    csv_path.write_text(
        "title,artist,source_url\n"
        "Song A,Artist A,http://example.com/a.mp3\n"
        "Song B,Artist B,http://example.com/b.mp3\n"
    )

    # Run the batch ingestion against the temporary DB
    result = await run_batch(csv_path=str(csv_path), db_path=str(temp_db))
    assert result == 0, "Batch job did not exit cleanly"

    # Verify records were inserted
    conn = sqlite3.connect(temp_db)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM media")
    count = cur.fetchone()[0]
    assert count == 2, f"Expected 2 media rows, got {count}"
