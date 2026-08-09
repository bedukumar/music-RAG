# LocalStack — Local Bulk Upload Development

This directory contains the Docker Compose configuration and initialisation
scripts for running S3 and SQS locally using
[LocalStack](https://localstack.cloud/).

---

## Prerequisites

| Tool | Install |
|---|---|
| Docker + Docker Compose | https://docs.docker.com/get-docker/ |
| `awslocal` CLI (optional, for manual inspection) | `pip install awscli-local` |
| boto3 | `pip install 'ragpipe[bulk]'` |
| openpyxl (for XLSX support) | included in `ragpipe[bulk]` |

---

## 1. Start LocalStack

```bash
docker compose -f deployment/localstack/docker-compose.localstack.yml up -d
```

Wait for the health check to pass (about 15–30 seconds):

```bash
docker compose -f deployment/localstack/docker-compose.localstack.yml ps
```

The `init-aws.sh` script runs automatically and creates:

- **S3 bucket**: `ragpipe-bulk-uploads`
- **SQS queue**: `ragpipe-bulk-uploads` (visibility timeout: 300 s, long-poll: 20 s)
- **SQS DLQ**: `ragpipe-bulk-uploads-dlq` (redrive after 5 receives)

Verify with:

```bash
awslocal --endpoint-url=http://localhost:4566 s3 ls
awslocal --endpoint-url=http://localhost:4566 sqs list-queues
```

---

## 2. Configure environment

```bash
# Copy the env file to the project root or source it directly
cp deployment/localstack/.env.localstack .env.localstack

# Source it (bash)
set -a && source .env.localstack && set +a
```

Or add the variables to your existing `.env` file:

```dotenv
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1
S3_BUCKET=ragpipe-bulk-uploads
S3_ENDPOINT_URL=http://localhost:4566
SQS_QUEUE_URL=http://localhost:4566/000000000000/ragpipe-bulk-uploads
SQS_DLQ_URL=http://localhost:4566/000000000000/ragpipe-bulk-uploads-dlq
SQS_ENDPOINT_URL=http://localhost:4566
SQS_VISIBILITY_TIMEOUT=300
SQS_MAX_RECEIVE_COUNT=5
```

---

## 3. Install bulk upload dependencies

```bash
pip install 'ragpipe[bulk]'
# installs: boto3, openpyxl
```

---

## 4. Start the API

```bash
uvicorn ragpipe.main:app --reload
```

The startup log should show:

```
bulk_upload_initialized  bucket=ragpipe-bulk-uploads  queue=http://localhost:4566/...
```

---

## 5. Start the bulk upload worker

In a separate terminal (with the same env vars):

```bash
python -m ragpipe.workers.bulk_upload_worker
```

---

## 6. Submit a bulk upload

Create a sample CSV:

```bash
cat > /tmp/sample_songs.csv << 'EOF'
title,media_type,artist,album,genre,language,tags
Bohemian Rhapsody,song,Queen,A Night at the Opera,rock,en,"classic,rock,70s"
Hotel California,song,Eagles,Hotel California,rock,en,"classic,rock,70s"
Stairway to Heaven,song,Led Zeppelin,Led Zeppelin IV,rock,en,"classic,rock,70s"
EOF
```

Submit it:

```bash
curl -s -X POST http://localhost:8000/api/v1/bulk-uploads \
  -F "file=@/tmp/sample_songs.csv;type=text/csv" | jq
```

Expected response (HTTP 202):

```json
{
  "bulk_upload_id": "...",
  "status": "PENDING"
}
```

---

## 7. Poll progress

```bash
# Replace {id} with the bulk_upload_id from step 6
curl -s http://localhost:8000/api/v1/bulk-uploads/{id} | jq

# Row-level results
curl -s "http://localhost:8000/api/v1/bulk-uploads/{id}/rows" | jq
```

---

## 8. Inspect LocalStack directly

```bash
# List uploaded files in S3
awslocal --endpoint-url=http://localhost:4566 s3 ls s3://ragpipe-bulk-uploads/ --recursive

# Inspect SQS queue depth
awslocal --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/ragpipe-bulk-uploads \
  --attribute-names ApproximateNumberOfMessages

# Inspect DLQ
awslocal --endpoint-url=http://localhost:4566 sqs get-queue-attributes \
  --queue-url http://localhost:4566/000000000000/ragpipe-bulk-uploads-dlq \
  --attribute-names ApproximateNumberOfMessages
```

---

## 9. Stop LocalStack

```bash
docker compose -f deployment/localstack/docker-compose.localstack.yml down
# Add -v to also remove the persistent data volume
docker compose -f deployment/localstack/docker-compose.localstack.yml down -v
```

---

## CSV/XLSX Column Reference

| Column | Required | Description |
|---|---|---|
| `title` | ✅ | Media title |
| `media_type` | ✅ | `song`, `podcast`, or `video` |
| `artist` | — | Artist / creator |
| `album` | — | Album / series |
| `genre` | — | Genre label |
| `language` | — | BCP-47 code (default: `en`) |
| `tags` | — | Comma-separated tags |
| `duration` | — | Duration in seconds |
| `source_url` | — | Original source URL |
| `audio_path` | — | Storage path for audio file |
| `transcript_text` | — | Full transcript / lyrics |
| `lyrics` | — | Song lyrics (song only) |
| `bpm` | — | Beats per minute (song only) |
| `musical_key` | — | Musical key e.g. `C#m` (song only) |
| `show_name` | — | Podcast show name (podcast only) |
| `episode_number` | — | Episode number (podcast only) |
| `host` | — | Podcast host (podcast only) |
| `guests` | — | Comma-separated guest names (podcast only) |
| `resolution` | — | Video resolution e.g. `1920x1080` (video only) |
| `fps` | — | Frames per second (video only) |
| `video_path` | — | Video file storage path (video only) |

Any extra columns are automatically stored in `metadata_fields`.
