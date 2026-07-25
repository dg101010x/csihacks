#!/usr/bin/env bash
# Shared config for infra/gcp/*.sh. Override any of these via environment
# variables before calling a script, e.g.:
#   GPU_PROFILE=g4-full ./infra/gcp/train_vm.sh
set -euo pipefail

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export BUCKET="${BUCKET:-${PROJECT_ID}-relieffm}"
export INSTANCE_NAME="${INSTANCE_NAME:-relieffm-train}"
export GPU_PROFILE="${GPU_PROFILE:-l4}"

case "$GPU_PROFILE" in
  l4)
    export REGION="${REGION:-us-east1}"
    export ZONE="${ZONE:-us-east1-b}"
    export MACHINE_TYPE="${MACHINE_TYPE:-g2-standard-4}"
    export GPU_TYPE="${GPU_TYPE:-nvidia-l4}"
    export BOOT_DISK_TYPE="${BOOT_DISK_TYPE:-pd-balanced}"
    export INCLUDE_ACCELERATOR_FLAG="${INCLUDE_ACCELERATOR_FLAG:-1}"
    export PROVISIONING_MODEL="${PROVISIONING_MODEL:-STANDARD}"
    ;;
  g4-full)
    export REGION="${REGION:-us-central1}"
    export ZONE="${ZONE:-us-central1-b}"
    export MACHINE_TYPE="${MACHINE_TYPE:-g4-standard-48}"
    export GPU_TYPE="${GPU_TYPE:-nvidia-rtx-pro-6000}"
    export BOOT_DISK_TYPE="${BOOT_DISK_TYPE:-hyperdisk-balanced}"
    export INCLUDE_ACCELERATOR_FLAG="${INCLUDE_ACCELERATOR_FLAG:-1}"
    export PROVISIONING_MODEL="${PROVISIONING_MODEL:-STANDARD}"
    ;;
  g4-full-flex)
    export REGION="${REGION:-us-central1}"
    export ZONE="${ZONE:-us-central1-b}"
    export MACHINE_TYPE="${MACHINE_TYPE:-g4-standard-48}"
    export GPU_TYPE="${GPU_TYPE:-nvidia-rtx-pro-6000}"
    export BOOT_DISK_TYPE="${BOOT_DISK_TYPE:-hyperdisk-balanced}"
    export INCLUDE_ACCELERATOR_FLAG="${INCLUDE_ACCELERATOR_FLAG:-1}"
    export PROVISIONING_MODEL="${PROVISIONING_MODEL:-FLEX_START}"
    ;;
  g4-full-vws)
    export REGION="${REGION:-us-central1}"
    export ZONE="${ZONE:-us-central1-b}"
    export MACHINE_TYPE="${MACHINE_TYPE:-g4-standard-48}"
    export GPU_TYPE="${GPU_TYPE:-nvidia-rtx-pro-6000-vws}"
    export BOOT_DISK_TYPE="${BOOT_DISK_TYPE:-hyperdisk-balanced}"
    export INCLUDE_ACCELERATOR_FLAG="${INCLUDE_ACCELERATOR_FLAG:-1}"
    export PROVISIONING_MODEL="${PROVISIONING_MODEL:-STANDARD}"
    ;;
  h100)
    export REGION="${REGION:-us-central1}"
    export ZONE="${ZONE:-us-central1-a}"
    export MACHINE_TYPE="${MACHINE_TYPE:-a3-highgpu-1g}"
    export GPU_TYPE="${GPU_TYPE:-nvidia-h100-80gb}"
    export BOOT_DISK_TYPE="${BOOT_DISK_TYPE:-hyperdisk-balanced}"
    # A3 machine types have GPUs pre-attached. The 1/2/4-GPU shapes must
    # use Spot or Flex-start; Flex-start avoids mid-run preemption.
    export INCLUDE_ACCELERATOR_FLAG="${INCLUDE_ACCELERATOR_FLAG:-0}"
    export PROVISIONING_MODEL="${PROVISIONING_MODEL:-FLEX_START}"
    ;;
  *)
    echo "unknown GPU_PROFILE=$GPU_PROFILE (expected l4, g4-full, g4-full-flex, g4-full-vws, or h100)" >&2
    exit 2
    ;;
esac

export GPU_COUNT="${GPU_COUNT:-1}"
export BOOT_DISK_SIZE_GB="${BOOT_DISK_SIZE_GB:-100}"
if [ "$PROVISIONING_MODEL" = "FLEX_START" ]; then
  export REQUEST_VALID_FOR_DURATION="${REQUEST_VALID_FOR_DURATION:-2h}"
  export MAX_VM_RUN_DURATION="${MAX_VM_RUN_DURATION:-12h}"
  export INSTANCE_TERMINATION_ACTION="${INSTANCE_TERMINATION_ACTION:-DELETE}"
fi
export IMAGE_FAMILY="${IMAGE_FAMILY:-pytorch-2-9-cu129-ubuntu-2204-nvidia-580}"  # Deep Learning VM: PyTorch + CUDA preinstalled
export IMAGE_PROJECT="${IMAGE_PROJECT:-deeplearning-platform-release}"

# MODEL_TARGET selects which training script run_pipeline.sh calls: "nano"
# (ml.training.train / ml.evaluation.run_eval) or "mini"
# (ml.training.train_mini / ml.evaluation.run_eval_mini).
export MODEL_TARGET="${MODEL_TARGET:-mini}"
# MODEL_PRESET selects the MiniConfig preset when MODEL_TARGET=mini: "mini"
# (~60M params, the validated one) or "flash" (~600M params, measured
# locally, not yet benchmarked on GPU -- see ml/relieffm/presets.py).
export MODEL_PRESET="${MODEL_PRESET:-mini}"

# Training hyperparameters for the real (non-smoke) run. Sized from an
# actual GPU benchmark pass on this same VM type: 0.81s/step measured at
# batch_size=32, n_scenarios_train=4 on a single L4 (2000-household,
# 1-epoch run). 25000 households / batch 32 -> ~625 steps/epoch; 12 epochs
# -> ~7500 steps -> ~101 min training, well inside a few-hours budget.
export N_HOUSEHOLDS="${N_HOUSEHOLDS:-25000}"
export EPOCHS="${EPOCHS:-12}"
export N_SCENARIOS_TRAIN="${N_SCENARIOS_TRAIN:-4}"
export N_SCENARIOS_EVAL="${N_SCENARIOS_EVAL:-8}"
if [ "$MODEL_PRESET" = "flash" ]; then
  case "$GPU_PROFILE" in
    l4)
      export BATCH_SIZE="${BATCH_SIZE:-1}"
      export GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-32}"
      ;;
    *)
      export BATCH_SIZE="${BATCH_SIZE:-4}"
      export GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-8}"
      ;;
  esac
  export ACTIVATION_CHECKPOINTING="${ACTIVATION_CHECKPOINTING:-1}"
  export LEARNING_RATE="${LEARNING_RATE:-2e-4}"
  # With an effective batch of 32, ~600 optimizer steps is approximately
  # one epoch for the default 25k-household split. Full validation is
  # expensive at Flash scale, so don't repeat Mini's every-200-step tax.
  export EVAL_EVERY_STEPS="${EVAL_EVERY_STEPS:-600}"
  export TRAIN_TIMEOUT="${TRAIN_TIMEOUT:-10h}"
else
  export BATCH_SIZE="${BATCH_SIZE:-32}"
  export GRADIENT_ACCUMULATION_STEPS="${GRADIENT_ACCUMULATION_STEPS:-1}"
  export ACTIVATION_CHECKPOINTING="${ACTIVATION_CHECKPOINTING:-0}"
  export LEARNING_RATE="${LEARNING_RATE:-3e-4}"
  export EVAL_EVERY_STEPS="${EVAL_EVERY_STEPS:-200}"
  export TRAIN_TIMEOUT="${TRAIN_TIMEOUT:-}"
fi
export RECOVERY_EVERY_STEPS="${RECOVERY_EVERY_STEPS:-100}"
export RUN_PREFLIGHT="${RUN_PREFLIGHT:-1}"
export PREFLIGHT_STEPS="${PREFLIGHT_STEPS:-3}"
export RESUME_GCS_URI="${RESUME_GCS_URI:-}"
export TRAIN_SEED="${TRAIN_SEED:-1}"
export EVAL_SEED="${EVAL_SEED:-99991}"
export RUN_ID="${RUN_ID:-${MODEL_TARGET}_$(date +%Y%m%d_%H%M%S)}"

echo "config: project=$PROJECT_ID zone=$ZONE bucket=gs://$BUCKET instance=$INSTANCE_NAME profile=$GPU_PROFILE provisioning=$PROVISIONING_MODEL machine=$MACHINE_TYPE gpu=${GPU_COUNT}x${GPU_TYPE} target=$MODEL_TARGET run_id=$RUN_ID" >&2
