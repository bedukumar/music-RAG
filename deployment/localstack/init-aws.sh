#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# init-aws.sh — LocalStack initialisation script
#
# This script runs automatically inside the LocalStack container once all
# requested services are ready (via the /etc/localstack/init/ready.d/ hook).
#
# It creates:
#   1. S3 bucket: ragpipe-bulk-uploads
#   2. SQS DLQ:   ragpipe-bulk-uploads-dlq
#   3. SQS queue: ragpipe-bulk-uploads (with redrive policy → DLQ)
# ---------------------------------------------------------------------------

set -e

ENDPOINT="http://localhost:4566"
REGION="us-east-1"
BUCKET="ragpipe-bulk-uploads"
QUEUE="ragpipe-bulk-uploads"
DLQ="ragpipe-bulk-uploads-dlq"
ACCOUNT_ID="000000000000"   # LocalStack default account ID

echo "==> Creating S3 bucket: ${BUCKET}"
awslocal s3api create-bucket \
  --bucket "${BUCKET}" \
  --region "${REGION}" 2>/dev/null || true

# Enable versioning so objects can be recovered (optional but recommended)
awslocal s3api put-bucket-versioning \
  --bucket "${BUCKET}" \
  --versioning-configuration Status=Enabled 2>/dev/null || true

echo "    S3 bucket ready: s3://${BUCKET}"

# ---------------------------------------------------------------------------
# SQS Dead-Letter Queue
# ---------------------------------------------------------------------------
echo "==> Creating SQS DLQ: ${DLQ}"
DLQ_URL=$(awslocal sqs create-queue \
  --queue-name "${DLQ}" \
  --attributes MessageRetentionPeriod=1209600 \
  --query QueueUrl --output text 2>/dev/null || true)

DLQ_ARN=$(awslocal sqs get-queue-attributes \
  --queue-url "${DLQ_URL}" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' --output text 2>/dev/null || true)

echo "    DLQ ARN: ${DLQ_ARN}"

# ---------------------------------------------------------------------------
# SQS Main Queue (with redrive policy → DLQ after 5 receives)
# ---------------------------------------------------------------------------
echo "==> Creating SQS queue: ${QUEUE}"
REDRIVE_POLICY='{\"deadLetterTargetArn\":\"'"${DLQ_ARN}"'\",\"maxReceiveCount\":\"5\"}'

QUEUE_URL=$(awslocal sqs create-queue \
  --queue-name "${QUEUE}" \
  --attributes '{"VisibilityTimeout":"300","MessageRetentionPeriod":"86400","ReceiveMessageWaitTimeSeconds":"20"}' \
  --query QueueUrl --output text)

awslocal sqs set-queue-attributes \
  --queue-url "${QUEUE_URL}" \
  --attributes '{"RedrivePolicy":"'"${REDRIVE_POLICY}"'"}'

echo "    Queue URL: ${QUEUE_URL}"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "==> LocalStack initialisation complete"
echo "    S3  bucket : s3://${BUCKET}"
echo "    SQS queue  : ${QUEUE_URL}"
echo "    SQS DLQ    : ${DLQ_URL}"
echo ""
echo "    Copy these URLs into .env.localstack if they differ from defaults."
