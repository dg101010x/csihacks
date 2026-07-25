#!/usr/bin/env bash
# Deletes the training VM. The startup script already shuts it down (so
# on-demand compute billing stops on its own), but the disk keeps costing
# a small amount until this runs.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

echo "deleting instance $INSTANCE_NAME in $ZONE ..."
gcloud compute instances delete "$INSTANCE_NAME" --zone "$ZONE" --project "$PROJECT_ID" --quiet
echo "done. Results remain at gs://$BUCKET/runs/ -- this does not delete the bucket."
