# ReliefFM (Plan One)

Implementation of `AGENTS_FM.md`'s Plan One workstream: ReliefFM Nano
(trained), Mini (trained), and Flash (606M-parameter training-ready
preset). See `ml/model_cards/` and `context.md` for verified results,
current infrastructure state, and limitations.

This directory is deliberately isolated from the rest of the repo — a
partner is building Plan Two (the consumer/provider app) separately, and
this workstream only talks to it through `packages/relief_contracts`.

## Layout

```
packages/relief_contracts/   shared request/response schemas (section 7-11)
ml/simulator/                 ReliefSim: synthetic household population generator
ml/datasets/                  compiles simulator output -> canonical events + Nano targets
ml/relieffm/                  Nano + Mini/Flash architectures and tokenizers
ml/training/                  training loops, recovery, losses, datasets, GPU preflight
ml/baselines/                 seasonal-median + gradient-boosted-trees baselines
ml/evaluation/                 trajectory/distress/calibration metrics + gate check
ml/calibration/                 temperature scaling (not applied by default this session)
ml/model_cards/                 model card + data card
services/model_inference/       FastAPI service implementing the 4 required endpoints
infra/gcp/                       gcloud/gsutil-only scripts to train on a GPU VM
tests/                           Stage Zero + pipeline tests
integration/                     trained Mini release manifest + Plan Two handoff
```

## Quickstart (local, CPU, no GCP)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .

pytest tests packages/relief_contracts/tests -q

python -m ml.training.train --n_households 500 --epochs 2 --out_dir runs/smoke
python -m ml.evaluation.run_eval --checkpoint_dir runs/smoke/checkpoint --n_households 300

RELIEFFM_CHECKPOINT_DIR=runs/smoke/checkpoint uvicorn services.model_inference.app:app --port 8080
```

For the trained Mini checkpoint and the exact Plan Two shadow-integration
steps, see `integration/README.md`.

## Training on GCP

```bash
cd infra/gcp
./setup.sh        # enable APIs, create the GCS bucket (idempotent)
./train_vm.sh      # packages code, provisions a GPU VM, runs sim+train+eval unattended
# poll: gcloud compute instances tail-serial-port-output relieffm-nano-train --zone <zone>
# or:   gcloud storage ls gs://<bucket>/runs/
./teardown.sh      # delete the VM once results are pulled (it self-shuts-down when done)
```

Edit `infra/gcp/config.sh` (or set env vars) to change project/zone/machine
type/GPU/household count/epochs. Everything goes through `gcloud`/`gsutil`.

Flash uses `MODEL_TARGET=mini MODEL_PRESET=flash`. The full 96 GB RTX PRO
6000 VWS profile is `GPU_PROFILE=g4-full-vws`. The pipeline runs a
full-update memory/throughput preflight before long training and uploads
recovery state before shutting down on failure.

## What's not here

Base, real/partner data adapters, fairness/privacy/robustness test suites,
distillation, and shadow deployment remain out of scope. See the model
cards for why each is a deliberate cut rather than an oversight.
