"""
End-to-End Bulk Upload Integration Test
========================================

Tests the FULL audio ingestion pipeline triggered via bulk upload.
Success is defined as vectors being physically stored in Qdrant —
not just a DB record existing.

Pipeline stages verified:
  upload → row registration → media_id → pipeline dispatch
  → validate → normalize → preprocess → chunk → embed
  → post_process → vector_storage ← REAL SUCCESS GATE

Run:
    bash tests/e2e/run_e2e.sh
or:
    venv/bin/python -m pytest tests/e2e/ -v -s --timeout=300 -m e2e

Prerequisites:
    - Server running  (docker-compose up  or  make dev)
    - Qdrant running  (included in docker-compose)
    - At least one MP3 file in ./data/uploads/
"""

from __future__ import annotations

import csv
import io
import os
import time
from pathlib import Path

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration — override via env vars if needed
# ---------------------------------------------------------------------------

API_BASE = os.getenv("RAGPIPE_API_BASE", "http://localhost:8000/api/v1")
QDRANT_BASE = os.getenv("QDRANT_BASE", "http://localhost:6333")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"

# Timeouts / poll intervals
BULK_UPLOAD_TIMEOUT_S = 60      # max wait for batch to reach COMPLETED
PIPELINE_TIMEOUT_S = 180        # max wait for audio pipeline to complete
POLL_INTERVAL_S = 3             # seconds between status checks

# Audio collection: f"{modality}_{embedding_version_id}"
# modality=audio, RAGPIPE_AUDIO_EMBEDDING_VERSION=v1  → "audio_v1"
AUDIO_COLLECTION = os.getenv("RAGPIPE_AUDIO_COLLECTION", "audio_v1")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_upload_mp3() -> str:
    """Return the relative audio_path of the first MP3 in data/uploads/.

    LocalFileStorage base = ./data  (STORAGE_PATH env default).
    So  data/uploads/xxx.mp3  is accessible as  uploads/xxx.mp3.
    """
    mp3s = sorted(UPLOADS_DIR.glob("*.mp3"))
    if not mp3s:
        pytest.skip(
            f"No MP3 files found in {UPLOADS_DIR}. "
            "Add at least one audio file to data/uploads/ before running e2e tests."
        )
    return f"uploads/{mp3s[0].name}"


def _build_csv(audio_path: str) -> bytes:
    """Build a minimal 1-row CSV that passes _build_media_item validation."""
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["title", "media_type", "audio_path", "artist", "genre", "tags"],
    )
    writer.writeheader()
    writer.writerow(
        {
            "title": "E2E Bulk Upload Test Track",
            "media_type": "song",
            "audio_path": audio_path,
            "artist": "E2E Test Artist",
            "genre": "electronic",
            "tags": "e2e,bulk-test,automated",
        }
    )
    return buf.getvalue().encode("utf-8")


def _poll(client: httpx.Client, url: str, check_fn, timeout: int, interval: int = POLL_INTERVAL_S):
    """Poll `url` until `check_fn(response_json)` returns a truthy value or timeout."""
    deadline = time.monotonic() + timeout
    last_data = None
    while time.monotonic() < deadline:
        resp = client.get(url)
        resp.raise_for_status()
        last_data = resp.json()
        result = check_fn(last_data)
        if result:
            return last_data, result
        time.sleep(interval)
    return last_data, None  # timed out


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

@pytest.mark.e2e
def test_bulk_upload_full_audio_pipeline():
    """
    Full end-to-end test:
        CSV bulk upload → audio pipeline completes → vectors stored in Qdrant.

    Six consecutive assertions, each building on the previous:
      1. HTTP 202 — upload accepted
      2. Bulk upload COMPLETED — all rows registered in DB
      3. media_id present — media record created and linked to row
      4. Audio pipeline completed — all 7 stages finished without error
      5. Qdrant scroll > 0 — vectors physically in the vector DB (REAL SUCCESS)
      6. /search returns media_id — vectors are semantically queryable
    """
    audio_path = _first_upload_mp3()
    csv_bytes = _build_csv(audio_path)

    print(f"\n[e2e] Using audio file: {audio_path}")
    print(f"[e2e] API base: {API_BASE}")
    print(f"[e2e] Qdrant:   {QDRANT_BASE}")

    with httpx.Client(base_url=API_BASE, timeout=30) as client:

        # ── Step 1: Upload CSV ─────────────────────────────────────────────
        print("\n[Step 1] Uploading bulk CSV...")
        resp = client.post(
            "/bulk-uploads",
            files={"file": ("e2e_test.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 202, (
            f"Expected 202, got {resp.status_code}: {resp.text}"
        )
        upload_data = resp.json()
        bulk_upload_id = upload_data["bulk_upload_id"]
        print(f"[Step 1] ✓  bulk_upload_id = {bulk_upload_id}")

        # ── Step 2: Poll until bulk upload COMPLETED ───────────────────────
        print("\n[Step 2] Waiting for bulk upload to complete (rows → DB)...")
        terminal = {"COMPLETED", "COMPLETED_WITH_ERRORS", "FAILED", "CANCELLED"}

        final_data, status = _poll(
            client,
            f"/bulk-uploads/{bulk_upload_id}",
            check_fn=lambda d: d.get("status") if d.get("status") in terminal else None,
            timeout=BULK_UPLOAD_TIMEOUT_S,
        )

        assert status is not None, (
            f"Bulk upload did not reach terminal status within {BULK_UPLOAD_TIMEOUT_S}s. "
            f"Last status: {final_data}"
        )
        assert status != "FAILED", (
            f"Bulk upload FAILED: {final_data.get('error_message')}"
        )
        print(f"[Step 2] ✓  status = {status}  "
              f"(successful_rows={final_data.get('successful_rows')}, "
              f"failed_rows={final_data.get('failed_rows')})")

        # ── Step 3: Get media_id from rows ────────────────────────────────
        print("\n[Step 3] Fetching row details to extract media_id...")
        rows_resp = client.get(f"/bulk-uploads/{bulk_upload_id}/rows")
        rows_resp.raise_for_status()
        rows = rows_resp.json().get("items", rows_resp.json().get("rows", []))

        processed_rows = [r for r in rows if r.get("status") == "processed" and r.get("media_id")]
        assert processed_rows, (
            f"No successfully processed rows found. Rows: {rows}"
        )
        media_id = processed_rows[0]["media_id"]
        print(f"[Step 3] ✓  media_id = {media_id}")

        # ── Step 4: Poll until audio pipeline completed ────────────────────
        print(f"\n[Step 4] Waiting for audio pipeline to complete (timeout={PIPELINE_TIMEOUT_S}s)...")

        def _audio_done(data: dict):
            pipelines = data.get("pipelines", {})
            audio = pipelines.get("audio", {})
            status = audio.get("overall_status", "")
            if status in ("completed", "failed"):
                return status
            return None

        final_pipeline, audio_status = _poll(
            client,
            f"/pipeline/status/{media_id}",
            check_fn=_audio_done,
            timeout=PIPELINE_TIMEOUT_S,
        )

        assert audio_status is not None, (
            f"Audio pipeline did not finish within {PIPELINE_TIMEOUT_S}s.\n"
            f"Last pipeline state: {final_pipeline}"
        )

        if audio_status == "failed":
            # Extract detailed stage errors for a clear failure message
            stages = (
                final_pipeline.get("pipelines", {})
                .get("audio", {})
                .get("stages", [])
            )
            failed_stages = [s for s in stages if s.get("status") == "failed"]
            errors = "\n".join(
                f"  stage={s['stage']}: {s.get('error_message', 'no detail')}"
                for s in failed_stages
            )
            pytest.fail(
                f"Audio pipeline FAILED for media_id={media_id}.\n"
                f"Failed stages:\n{errors}\n"
                f"Full pipeline state:\n{final_pipeline}"
            )

        # Verify all stages completed
        stages = (
            final_pipeline.get("pipelines", {})
            .get("audio", {})
            .get("stages", [])
        )
        stage_statuses = {s["stage"]: s["status"] for s in stages}
        print(f"[Step 4] ✓  audio pipeline = {audio_status}")
        print(f"           Stage breakdown: {stage_statuses}")

        non_completed = {k: v for k, v in stage_statuses.items() if v != "completed"}
        assert not non_completed, (
            f"Some pipeline stages did not complete: {non_completed}"
        )

    # ── Step 5: Verify vectors in Qdrant ─────────────────────────────────
    print(f"\n[Step 5] Querying Qdrant for vectors (media_id={media_id})...")
    print(f"         Collection: {AUDIO_COLLECTION}")

    with httpx.Client(base_url=QDRANT_BASE, timeout=30) as qdrant:

        # First confirm collection exists (auto-detect if name differs)
        collections_resp = qdrant.get("/collections")
        collections_resp.raise_for_status()
        collection_names = [
            c["name"]
            for c in collections_resp.json().get("result", {}).get("collections", [])
        ]
        print(f"         Available collections: {collection_names}")

        # Try exact name first, then fall back to any collection starting with "audio"
        target_collection = AUDIO_COLLECTION
        if target_collection not in collection_names:
            audio_collections = [n for n in collection_names if n.startswith("audio")]
            assert audio_collections, (
                f"No audio collection found in Qdrant. "
                f"Available: {collection_names}\n"
                f"Pipeline claimed to complete — is Qdrant reachable at {QDRANT_BASE}?"
            )
            target_collection = audio_collections[0]
            print(f"         (Fell back to collection: {target_collection})")

        # Scroll with media_id filter
        scroll_resp = qdrant.post(
            f"/collections/{target_collection}/points/scroll",
            json={
                "with_payload": True,
                "with_vector": False,
                "limit": 20,
                "filter": {
                    "must": [
                        {"key": "media_id", "match": {"value": media_id}}
                    ]
                },
            },
        )
        scroll_resp.raise_for_status()
        points = scroll_resp.json().get("result", {}).get("points", [])

        print(f"         Vectors found: {len(points)}")
        if points:
            sample = points[0]
            print(f"         Sample point id={sample['id']}, "
                  f"payload={sample.get('payload', {})}")

        assert len(points) > 0, (
            f"❌  REAL FAILURE: Audio pipeline reported 'completed' but NO vectors "
            f"found in Qdrant collection '{target_collection}' for media_id={media_id}.\n"
            f"This means vector_storage stage silently failed or stored to a different collection."
        )

        # Verify payload integrity
        for point in points:
            payload = point.get("payload", {})
            assert payload.get("media_id") == media_id, (
                f"Vector point {point['id']} has wrong media_id in payload: {payload}"
            )
            assert payload.get("modality") == "audio", (
                f"Vector point has wrong modality: {payload}"
            )

        print(f"[Step 5] ✓  {len(points)} audio vectors stored in Qdrant '{target_collection}'")
        print(f"           Payload keys: {list(points[0].get('payload', {}).keys())}")

    # ── Step 6: Verify vectors are searchable via /search ─────────────────
    print("\n[Step 6] Verifying vectors are semantically searchable...")
    with httpx.Client(base_url=API_BASE, timeout=30) as client:
        search_resp = client.post(
            "/search",
            json={
                "query": "E2E Test Artist electronic",
                "modalities": ["audio"],
                "top_k": 10,
                "score_threshold": 0.0,
            },
        )
        search_resp.raise_for_status()
        results = search_resp.json().get("results", [])
        result_media_ids = [r.get("media_id") for r in results]

        print(f"         Search returned {len(results)} results")
        print(f"         media_ids in results: {result_media_ids[:5]}")

        assert media_id in result_media_ids, (
            f"❌  SEARCH FAILURE: media_id={media_id} not found in search results.\n"
            f"Vectors exist in Qdrant but search didn't return them.\n"
            f"Results: {result_media_ids}"
        )
        print(f"[Step 6] ✓  media_id found in search results")

    # ── All assertions passed ─────────────────────────────────────────────
    print(f"""
╔══════════════════════════════════════════════════════════╗
║  ✅  BULK UPLOAD E2E TEST PASSED                         ║
╠══════════════════════════════════════════════════════════╣
║  bulk_upload_id : {bulk_upload_id:<38} ║
║  media_id       : {media_id:<38} ║
║  audio_path     : {audio_path:<38} ║
║  collection     : {target_collection:<38} ║
║  vectors stored : {str(len(points)):<38} ║
╚══════════════════════════════════════════════════════════╝
""")
