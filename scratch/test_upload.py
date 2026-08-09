import requests
import time

print("Uploading CSV...")
with open("scratch/test_upload.csv", "rb") as f:
    files = {"file": f}
    resp = requests.post("http://localhost:8000/api/v1/bulk-uploads", files=files)

print(resp.status_code, resp.text)
if resp.status_code >= 300:
    exit(1)

data = resp.json()
bulk_id = data["bulk_upload_id"]
print(f"Bulk ID: {bulk_id}")

print("Waiting for bulk upload worker...")
for i in range(15):
    time.sleep(2)
    st = requests.get(f"http://localhost:8000/api/v1/bulk-uploads/{bulk_id}").json()
    print(f"Status: {st.get('status')}, Processed: {st.get('processed_rows')}, Failed: {st.get('failed_rows')}")
    if st.get("status") in ("completed", "completed_with_errors", "failed"):
        break

print("\nFetching errors if any:")
errs = requests.get(f"http://localhost:8000/api/v1/bulk-uploads/{bulk_id}/errors").json()
print(errs)

print("\nChecking Jobs...")
jobs = requests.get("http://localhost:8000/api/v1/jobs").json()
print("Recent Jobs:")
for j in jobs.get("items", [])[:10]:
    print(f"- Job {j.get('id')}: {j.get('job_type')} -> {j.get('status')} | Media: {j.get('media_id')}")

print("\nChecking Media Items...")
media = requests.get("http://localhost:8000/api/v1/media").json()
print("Recent Media:")
for m in media.get("items", [])[:3]:
    print(f"- {m.get('title')} ({m.get('media_type')}) - ID: {m.get('id')} - Audio: {m.get('audio_path')}")
