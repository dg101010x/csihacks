#!/usr/bin/env bash
# Runs ON the training VM (invoked by the startup-script). Not meant to be
# run locally. Reads its config from environment variables baked into VM
# metadata by train_vm.sh.
set -euo pipefail
export PYTHONUNBUFFERED=1  # otherwise python's stdout block-buffers when piped through tee,
                             # and the serial console / log file can lag several minutes behind
                             # actual progress (harmless but confusing -- looked like a hang on
                             # the Mini run when it wasn't one; ps/nvidia-smi via SSH confirmed
                             # the process was fine, just not flushing output).
exec > >(tee -a /var/log/relieffm_pipeline.log) 2>&1

pipeline_cleanup() {
  status=$?
  if [ "$status" -ne 0 ]; then
    echo "pipeline failed with status=$status; uploading logs/recovery and stopping VM"
    if [ -d "/opt/relieffm/runs/$RUN_ID" ]; then
      gcloud storage cp -r "/opt/relieffm/runs/$RUN_ID" \
        "gs://$BUCKET/runs/$RUN_ID" || true
    fi
    gcloud storage cp /var/log/relieffm_pipeline.log \
      "gs://$BUCKET/runs/$RUN_ID/pipeline.log" || true
    sudo shutdown -h now || true
  fi
  return "$status"
}
trap pipeline_cleanup EXIT

echo "=== relieffm pipeline start: $(date -u) ==="

WORKDIR=/opt/relieffm
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "downloading code from gs://$BUCKET/code/relieffm.tar.gz ..."
gcloud storage cp "gs://$BUCKET/code/relieffm.tar.gz" ./relieffm.tar.gz
tar -xzf relieffm.tar.gz
# train_vm.sh archives REPO_ROOT's *contents* (tar -C "$REPO_ROOT" .), so
# they land directly in $WORKDIR -- no nested relieffm/ dir to cd into.

echo "installing dependencies..."
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e .

echo "checking GPU visibility to torch..."
if ! python3 -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then
  echo "torch.cuda.is_available() is False -- the DLVM's preinstalled torch build wasn't picked up, or CUDA isn't visible. Reinstalling a CUDA build explicitly."
  nvidia-smi || echo "WARNING: nvidia-smi failed -- GPU driver may not be ready"
  python3 -m pip install --quiet --force-reinstall torch --index-url https://download.pytorch.org/whl/cu121
  python3 -c "import torch; print('cuda available:', torch.cuda.is_available()); print('device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
else
  python3 -c "import torch; print('cuda available: True, device:', torch.cuda.get_device_name(0))"
fi

MODEL_TARGET="${MODEL_TARGET:-nano}"
MODEL_PRESET="${MODEL_PRESET:-mini}"   # "mini" or "flash" -- only used when MODEL_TARGET=mini

if [ "$MODEL_TARGET" = "mini" ]; then
  train_extra_args=(
    --gradient_accumulation_steps "$GRADIENT_ACCUMULATION_STEPS"
    --recovery_every_steps "$RECOVERY_EVERY_STEPS"
    --lr "$LEARNING_RATE"
    --eval_every_steps "$EVAL_EVERY_STEPS"
  )
  if [ "${ACTIVATION_CHECKPOINTING:-0}" = "1" ]; then
    train_extra_args+=(--activation_checkpointing)
  fi
  if [ -n "${RESUME_GCS_URI:-}" ]; then
    echo "downloading recovery state from $RESUME_GCS_URI ..."
    mkdir -p "runs/$RUN_ID"
    gcloud storage cp -r "$RESUME_GCS_URI" "runs/$RUN_ID/"
    train_extra_args+=(--resume_from "runs/$RUN_ID/recovery")
  fi
  if [ "${RUN_PREFLIGHT:-1}" = "1" ]; then
    preflight_extra_args=()
    if [ "${ACTIVATION_CHECKPOINTING:-0}" = "1" ]; then
      preflight_extra_args+=(--activation_checkpointing)
    fi
    echo "running full-update GPU preflight before long training..."
    python3 -m ml.training.benchmark_mini \
      --preset "$MODEL_PRESET" \
      --batch_size "$BATCH_SIZE" \
      --n_scenarios "$N_SCENARIOS_TRAIN" \
      --steps "$PREFLIGHT_STEPS" \
      --out_path "runs/$RUN_ID/preflight.json" \
      "${preflight_extra_args[@]}"
  fi

  echo "training MINI (preset=$MODEL_PRESET): n_households=$N_HOUSEHOLDS epochs=$EPOCHS batch_size=$BATCH_SIZE n_scenarios_train=$N_SCENARIOS_TRAIN seed=$TRAIN_SEED"
  train_command=(python3 -m ml.training.train_mini
    --preset "$MODEL_PRESET"
    --n_households "$N_HOUSEHOLDS"
    --epochs "$EPOCHS"
    --batch_size "$BATCH_SIZE"
    --n_scenarios_train "$N_SCENARIOS_TRAIN"
    --n_scenarios_eval "$N_SCENARIOS_EVAL"
    --seed "$TRAIN_SEED"
    --out_dir "runs/$RUN_ID"
    "${train_extra_args[@]}")
  if [ -n "${TRAIN_TIMEOUT:-}" ]; then
    timeout --signal=TERM --kill-after=5m "$TRAIN_TIMEOUT" "${train_command[@]}"
  else
    "${train_command[@]}"
  fi

  echo "evaluating..."
  python3 -m ml.evaluation.run_eval_mini \
    --checkpoint_dir "runs/$RUN_ID/checkpoint_best" \
    --n_households 1500 \
    --n_scenarios 16 \
    --seed "$EVAL_SEED" \
    --out_path "runs/$RUN_ID/eval_report.json"
else
  echo "training NANO: n_households=$N_HOUSEHOLDS epochs=$EPOCHS batch_size=$BATCH_SIZE seed=$TRAIN_SEED"
  python3 -m ml.training.train \
    --n_households "$N_HOUSEHOLDS" \
    --epochs "$EPOCHS" \
    --batch_size "$BATCH_SIZE" \
    --seed "$TRAIN_SEED" \
    --out_dir "runs/$RUN_ID"

  echo "evaluating..."
  python3 -m ml.evaluation.run_eval \
    --checkpoint_dir "runs/$RUN_ID/checkpoint" \
    --n_households 1500 \
    --seed "$EVAL_SEED" \
    --out_path "runs/$RUN_ID/eval_report.json"
fi

echo "uploading results to gs://$BUCKET/runs/$RUN_ID/ ..."
gcloud storage cp -r "runs/$RUN_ID" "gs://$BUCKET/runs/$RUN_ID"
gcloud storage cp /var/log/relieffm_pipeline.log "gs://$BUCKET/runs/$RUN_ID/pipeline.log" || true

echo "=== relieffm pipeline done: $(date -u) ==="
echo "shutting down to stop billing (VM stays allocated -- run teardown.sh to delete it)"
sudo shutdown -h now
