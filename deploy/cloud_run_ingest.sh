#!/usr/bin/env bash
# Build the ingest image, push to Artifact Registry, create or update the Cloud Run Job.
# Prerequisites: gcloud auth, project set, APIs enabled (see deploy/README.md).
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-kalshi-analytics-512607}"
REGION="${REGION:-us-central1}"
REPOSITORY="${REPOSITORY:-kalshi}"
IMAGE_NAME="${IMAGE_NAME:-chess-ingest}"
JOB_NAME="${JOB_NAME:-chess-ingest}"
RUN_SA="${RUN_SA:-chess-ingest@${PROJECT_ID}.iam.gserviceaccount.com}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"

gcloud config set project "${PROJECT_ID}"

gcloud services enable run.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com

if ! gcloud artifacts repositories describe "${REPOSITORY}" --location="${REGION}" &>/dev/null; then
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Kalshi analytics containers"
fi

gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

docker build -t "${IMAGE}" "${ROOT}"
docker push "${IMAGE}"

if ! gcloud iam service-accounts describe "${RUN_SA}" &>/dev/null; then
  gcloud iam service-accounts create chess-ingest \
    --display-name="Chess ingest Cloud Run Job"
  RUN_SA="chess-ingest@${PROJECT_ID}.iam.gserviceaccount.com"
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/bigquery.dataEditor" \
    --quiet
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUN_SA}" \
    --role="roles/bigquery.jobUser" \
    --quiet
fi

if gcloud run jobs describe "${JOB_NAME}" --region="${REGION}" &>/dev/null; then
  gcloud run jobs update "${JOB_NAME}" \
    --region="${REGION}" \
    --image="${IMAGE}" \
    --service-account="${RUN_SA}" \
    --task-timeout=3600 \
    --max-retries=1 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
else
  gcloud run jobs create "${JOB_NAME}" \
    --region="${REGION}" \
    --image="${IMAGE}" \
    --service-account="${RUN_SA}" \
    --task-timeout=3600 \
    --max-retries=1 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
fi

echo "Run once: gcloud run jobs execute ${JOB_NAME} --region=${REGION} --wait"
