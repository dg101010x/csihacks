#!/usr/bin/env bash
# Bounded, useful CPU validation run for establishing project billing history.
# The VM also has a provider-enforced maximum duration and DELETE action.
set -euo pipefail
export PYTHONUNBUFFERED=1

LOG_PATH=/var/log/relieffm_cpu_history.log
exec > >(tee -a "$LOG_PATH") 2>&1

metadata() {
  curl --fail --silent \
    -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"
}

BUCKET="$(metadata relieffm-bucket)"
SOURCE_OBJECT="$(metadata relieffm-source-object)"
RUN_ID="$(metadata relieffm-run-id)"
WORKDIR=/opt/relieffm
RESULT_DIR="$WORKDIR/runs/$RUN_ID"

upload_results() {
  status=$?
  python3 - "$BUCKET" "$RUN_ID" "$RESULT_DIR" "$LOG_PATH" <<'PY' || true
import sys
from pathlib import Path

from google.cloud import storage

bucket_name, run_id, result_dir, log_path = sys.argv[1:]
bucket = storage.Client().bucket(bucket_name)
root = Path(result_dir)
if root.exists():
    for path in root.rglob("*"):
        if path.is_file():
            relative = path.relative_to(root).as_posix()
            bucket.blob(f"history/{run_id}/{relative}").upload_from_filename(path)
log = Path(log_path)
if log.is_file():
    bucket.blob(f"history/{run_id}/cpu_history.log").upload_from_filename(log)
PY
  shutdown -h now || true
  return "$status"
}
trap upload_results EXIT

echo "=== ReliefFM Compute CPU history run: $(date -u) ==="
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3-pip
python3 -m pip install --quiet --upgrade pip google-cloud-storage

mkdir -p "$WORKDIR"
python3 - "$BUCKET" "$SOURCE_OBJECT" "$WORKDIR/source.tar.gz" <<'PY'
import sys
from google.cloud import storage

bucket_name, object_name, destination = sys.argv[1:]
storage.Client().bucket(bucket_name).blob(object_name).download_to_filename(destination)
PY
tar -xzf "$WORKDIR/source.tar.gz" -C "$WORKDIR"
cd "$WORKDIR"
python3 -m pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu
python3 -m pip install --quiet -e .

python3 -m pytest -q
timeout --signal=TERM --kill-after=2m 42m \
  python3 -m ml.training.train \
    --n_households 5000 \
    --epochs 1 \
    --batch_size 64 \
    --seed 20260725 \
    --out_dir "$RESULT_DIR"

echo "=== ReliefFM Compute CPU history run complete: $(date -u) ==="
