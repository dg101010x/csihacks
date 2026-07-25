#!/usr/bin/env bash
# One-time setup: enable APIs, create the GCS bucket. gcloud/gsutil only,
# no console steps.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

echo "enabling required APIs..."
gcloud services enable compute.googleapis.com storage.googleapis.com --project "$PROJECT_ID"

if ! gcloud storage buckets describe "gs://$BUCKET" >/dev/null 2>&1; then
  echo "creating gs://$BUCKET in $REGION..."
  gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT_ID" --location "$REGION"
else
  echo "gs://$BUCKET already exists"
fi

echo "setup complete."
