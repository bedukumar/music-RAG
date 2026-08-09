import requests

jobs = requests.get("http://localhost:8000/api/v1/jobs").json()
media_items = requests.get("http://localhost:8000/api/v1/media").json().get("items", [])

# Find the most recently created media item
if not media_items:
    print("No media items found")
    exit(0)

# The API likely returns descending or ascending. Let's just find the one named "Moments "
target_media = next((m for m in media_items if m.get("title", "").strip() == "Moments"), None)
if not target_media:
    # try picking the last one
    target_media = media_items[-1]

media_id = target_media["id"]
print(f"Target Media: {target_media['title']} (ID: {media_id})")
print(f"  Source URL: {target_media.get('source_url')}")
print(f"  Audio Path: {target_media.get('audio_path')}")

print("\nJobs for this media:")
found_jobs = False
for j in jobs.get("items", []):
    if j.get("media_id") == media_id:
        print(f"- Job {j.get('id')}: Modality={j.get('modality')} Status={j.get('status')}")
        found_jobs = True

if not found_jobs:
    print("NO JOBS FOUND FOR THIS MEDIA")
