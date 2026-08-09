import sqlite3
import sys

conn = sqlite3.connect("ragpipe.db")
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("SELECT * FROM media_items ORDER BY created_at DESC LIMIT 1")
media = c.fetchone()
if not media:
    print("No media items found")
    sys.exit(0)

media_id = media["id"]
print(f"Latest Media ID: {media_id}")
print(f"Title: {media['title']}")
print(f"Source URL: {media['source_url']}")

print("\n--- Modality Statuses ---")
c.execute("SELECT modality, data_available, embedding_status FROM modality_statuses WHERE media_id=?", (media_id,))
for row in c.fetchall():
    print(dict(row))
    
print("\n--- Jobs ---")
c.execute("SELECT id, modality, status FROM jobs WHERE media_id=?", (media_id,))
jobs = c.fetchall()
if not jobs:
    print("No jobs found for this media id in DB!")
else:
    for row in jobs:
        print(dict(row))
