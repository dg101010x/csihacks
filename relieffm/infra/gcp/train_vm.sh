#!/usr/bin/env bash
# Packages the code, uploads it to GCS, and provisions a single GPU VM that
# runs the full simulate -> train -> evaluate pipeline unattended, uploads
# results back to GCS, then shuts itself down (stops billing; does not
# delete the VM -- run teardown.sh after you've pulled results).
#
# Everything here is gcloud/gsutil -- no console steps.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh
REPO_ROOT="$(cd .. && cd .. && pwd)"

echo "packaging code from $REPO_ROOT ..."
TARBALL="$(mktemp -t relieffm-code-XXXXXX)"
# COPYFILE_DISABLE avoids macOS bsdtar writing AppleDouble/xattr headers
# that GNU tar on the Linux VM can't parse (just noisy warnings, but why
# ship them).
COPYFILE_DISABLE=1 tar -czf "$TARBALL" \
  --exclude='.venv' --exclude='.git' --exclude='runs' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.egg-info' \
  -C "$REPO_ROOT" .

echo "uploading code to gs://$BUCKET/code/relieffm.tar.gz ..."
gcloud storage cp "$TARBALL" "gs://$BUCKET/code/relieffm.tar.gz"
rm -f "$TARBALL"

STARTUP_SCRIPT="$(mktemp -t relieffm-startup-XXXX.sh)"
cat > "$STARTUP_SCRIPT" <<EOF
#!/usr/bin/env bash
export BUCKET="$BUCKET"
export MODEL_TARGET="$MODEL_TARGET"
export MODEL_PRESET="$MODEL_PRESET"
export N_HOUSEHOLDS="$N_HOUSEHOLDS"
export EPOCHS="$EPOCHS"
export BATCH_SIZE="$BATCH_SIZE"
export N_SCENARIOS_TRAIN="$N_SCENARIOS_TRAIN"
export N_SCENARIOS_EVAL="$N_SCENARIOS_EVAL"
export GRADIENT_ACCUMULATION_STEPS="$GRADIENT_ACCUMULATION_STEPS"
export RECOVERY_EVERY_STEPS="$RECOVERY_EVERY_STEPS"
export ACTIVATION_CHECKPOINTING="$ACTIVATION_CHECKPOINTING"
export LEARNING_RATE="$LEARNING_RATE"
export EVAL_EVERY_STEPS="$EVAL_EVERY_STEPS"
export RUN_PREFLIGHT="$RUN_PREFLIGHT"
export PREFLIGHT_STEPS="$PREFLIGHT_STEPS"
export TRAIN_TIMEOUT="$TRAIN_TIMEOUT"
export RESUME_GCS_URI="$RESUME_GCS_URI"
export TRAIN_SEED="$TRAIN_SEED"
export EVAL_SEED="$EVAL_SEED"
export RUN_ID="$RUN_ID"
$(cat ./run_pipeline.sh | tail -n +2)
EOF

create_args=(
  "$INSTANCE_NAME"
  --project "$PROJECT_ID"
  --zone "$ZONE"
  --machine-type "$MACHINE_TYPE"
  --image-family "$IMAGE_FAMILY"
  --image-project "$IMAGE_PROJECT"
  --boot-disk-size "${BOOT_DISK_SIZE_GB}GB"
  --boot-disk-type "$BOOT_DISK_TYPE"
  --maintenance-policy TERMINATE
  --no-restart-on-failure
  --scopes cloud-platform
  --metadata-from-file startup-script="$STARTUP_SCRIPT"
)
if [ "$INCLUDE_ACCELERATOR_FLAG" = "1" ]; then
  create_args+=(--accelerator "type=$GPU_TYPE,count=$GPU_COUNT")
fi
if [ "$PROVISIONING_MODEL" = "FLEX_START" ]; then
  create_args+=(
    --provisioning-model FLEX_START
    --request-valid-for-duration "$REQUEST_VALID_FOR_DURATION"
    --max-run-duration "$MAX_VM_RUN_DURATION"
    --instance-termination-action "$INSTANCE_TERMINATION_ACTION"
    --reservation-affinity none
  )
fi

echo "estimated cost: ${MACHINE_TYPE} + ${GPU_COUNT}x ${GPU_TYPE} in ${ZONE}, provisioning=$PROVISIONING_MODEL -- check current pricing at https://cloud.google.com/products/compute/pricing/accelerator-optimized before large runs."
echo "creating instance $INSTANCE_NAME in $ZONE ..."
gcloud compute instances create "${create_args[@]}"

rm -f "$STARTUP_SCRIPT"

echo "instance created. Tail progress with:"
echo "  gcloud compute instances tail-serial-port-output $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID"
echo "Or poll gs://$BUCKET/runs/$RUN_ID/ for results. The VM shuts itself down when done -- run teardown.sh afterward."
echo "RUN_ID=$RUN_ID"
