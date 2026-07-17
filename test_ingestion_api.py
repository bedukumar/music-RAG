import os
import sys
import time
import requests
from urllib.error import URLError

BASE_URL = "http://localhost:8000/api/v1"

def test_ingestion(file_path: str, title: str, artist: str = "Unknown"):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

    print(f"Uploading '{file_path}' as '{title}' by '{artist}'...")

    # 1. Upload the media file
    upload_url = f"{BASE_URL}/media/upload"
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "audio/mpeg")}
            response = requests.post(upload_url, files=files)
            response.raise_for_status()
            upload_data = response.json()
            audio_path = upload_data.get("path")
            print(f"✅ Upload successful! File saved at: {audio_path}")
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {BASE_URL}.")
        print("Make sure the FastAPI server is running (uvicorn ragpipe.main:app --reload).")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {e}")
        sys.exit(1)

    # 2. Create the media item
    create_url = f"{BASE_URL}/media"
    data = {
        "media_type": "song",
        "title": title,
        "artist": artist,
        "genre": "Pop",
        "audio_path": audio_path,
        "transcript_text": "These are some dummy lyrics for the transcript pipeline to process.",
        "metadata_fields": {"album": "Greatest Hits", "year": "2000"}
    }
    
    response = requests.post(create_url, json=data)
    response.raise_for_status()
    media = response.json()
    media_id = media.get("id")
    print(f"✅ Media created successfully! Media ID: {media_id}")
    
    # 3. Trigger processing
    process_url = f"{BASE_URL}/media/{media_id}/process"
    process_data = {
        "modalities": ["audio", "transcript", "metadata"]
    }
    response = requests.post(process_url, json=process_data)
    response.raise_for_status()
    print(f"✅ Processing triggered!")

    # 4. Poll for job completion
    print("\nPolling for job statuses... (Press Ctrl+C to stop)")
    status_url = f"{BASE_URL}/jobs"
    
    try:
        while True:
            resp = requests.get(status_url, params={"limit": 50})
            if resp.status_code == 200:
                resp_json = resp.json()
                jobs = resp_json.get("items", [])
                
                # Filter jobs for our newly created media
                media_jobs = [j for j in jobs if j.get("media_id") == media_id]
                
                if not media_jobs:
                    print("Waiting for background tasks to create jobs...")
                else:
                    all_completed = True
                    print(f"\n--- Job Statuses for {media_id} ---")
                    for job in media_jobs:
                        mod = job.get("modality", "unknown")
                        status = job.get("status", "unknown")
                        error = job.get("error_message", "")
                        
                        if status == "failed":
                            print(f"  [{mod.upper()}] Status: {status} | Error: {error}")
                        else:
                            print(f"  [{mod.upper()}] Status: {status}")
                            
                        if status not in ("completed", "failed"):
                            all_completed = False
                            
                    if all_completed:
                        print("\n✅ All jobs have completed (or failed) for this media.")
                        break
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nPolling stopped.")

if __name__ == "__main__":
    test_file = "Westlife.mp3"
    
    if not os.path.exists(test_file):
        print(f"Warning: {test_file} not found. Creating a temporary dummy file...")
        test_file = "dummy_test.mp3"
        with open(test_file, "wb") as f:
            f.write(b"fake mp3 content")

    test_ingestion(test_file, title="My Love", artist="Westlife")
    
    if test_file == "dummy_test.mp3" and os.path.exists(test_file):
        os.remove(test_file)
