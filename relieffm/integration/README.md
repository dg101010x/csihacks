# ReliefFM Mini integration handoff

This directory is the Plan One handoff for connecting the trained Mini
checkpoint to Plan Two's model gateway. The only safe launch mode is
**shadow**: Plan Two continues to display and act on its deterministic
provider while ReliefFM runs in parallel for comparison and logging.

## Release

- Run: `mini_20260725_122238`
- Model: `relieffm_mini` `0.1.0`, 59,641,666 parameters
- Contract: `1.0.0`
- Input: USD `HouseholdSnapshotV1`
- Serving shape: one 60-day horizon, up to 64 scenarios
- Checkpoint:
  `gs://cerebrum-research-relieffm/runs/mini_20260725_122238/checkpoint`
- Full provenance and hashes:
  `mini_20260725_122238.release.json`

The checkpoint and dataset are deliberately excluded from Git. The
release manifest is the small, reviewable pointer to the GCS artifacts.

## Pull and verify the serving checkpoint

From `relieffm/`:

```bash
mkdir -p runs/mini_20260725_122238/checkpoint
gcloud storage cp \
  gs://cerebrum-research-relieffm/runs/mini_20260725_122238/checkpoint/checkpoint_meta.json \
  runs/mini_20260725_122238/checkpoint/
gcloud storage cp \
  gs://cerebrum-research-relieffm/runs/mini_20260725_122238/checkpoint/model.safetensors \
  runs/mini_20260725_122238/checkpoint/

shasum -a 256 \
  runs/mini_20260725_122238/checkpoint/checkpoint_meta.json \
  runs/mini_20260725_122238/checkpoint/model.safetensors
```

The expected hashes are in the release manifest. `training_state.pt` is
only needed to resume training and should not be copied into a serving
image.

## Start the API

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

RELIEFFM_CHECKPOINT_DIR=runs/mini_20260725_122238/checkpoint \
RELIEFFM_DEVICE=auto \
uvicorn services.model_inference.app:app --host 0.0.0.0 --port 8080
```

`RELIEFFM_DEVICE=auto` selects CUDA when available and otherwise uses CPU.
An explicit unavailable or invalid device fails readiness instead of
silently serving on the wrong hardware.

For a containerized CPU smoke test:

```bash
RELIEFFM_CHECKPOINT_HOST_DIR="$PWD/runs/mini_20260725_122238/checkpoint" \
docker compose -f integration/docker-compose.yml up --build
```

The image is CUDA-capable, but the checked-in Compose file stays on CPU
so it runs everywhere. A GPU deployment should add the platform's GPU
reservation and set `RELIEFFM_DEVICE=cuda`.

## Gateway contract

The generated handoff under `generated/` contains:

- JSON Schema for every shared request/response type
- OpenAPI for all four model endpoints
- Valid forecast and intervention requests
- Responses produced by this exact trained checkpoint with a fixed seed

Rebuild it after any contract or checkpoint change:

```bash
python -m relief_contracts.export_integration_bundle \
  integration/generated \
  --checkpoint-dir runs/mini_20260725_122238/checkpoint
```

Plan Two should configure:

```text
base URL:       http://<relieffm-host>:8080
mode:           shadow
timeout action: cancel/ignore ReliefFM result and use deterministic provider
cache key:      snapshot + horizon + scenarios + model/calibration version + intervention
supported:      USD, horizon_days=60, scenario_count=0..64
```

Required endpoints:

- `GET /model/v1/health`
- `GET /model/v1/metadata`
- `POST /model/v1/forecast`
- `POST /model/v1/simulate_intervention`

Smoke the live server with the generated fixtures:

```bash
curl --fail http://127.0.0.1:8080/model/v1/health
curl --fail \
  -H 'content-type: application/json' \
  --data @integration/generated/fixtures/forecast_request.json \
  http://127.0.0.1:8080/model/v1/forecast
curl --fail \
  -H 'content-type: application/json' \
  --data @integration/generated/fixtures/intervention_request.json \
  http://127.0.0.1:8080/model/v1/simulate_intervention
```

## What Plan Two must enforce

1. Construct and validate the complete snapshot. ReliefFM never queries
   the app database.
2. Run ReliefFM beside the deterministic forecast. Do not replace the
   deterministic result.
3. Store both outputs, model warnings, latency, reconciliation failures,
   contract version, model version, dataset version, and calibration
   version.
4. Reject stale, timed-out, malformed, or unreconciled model responses.
5. Never let a model endpoint approve or execute a financial action.
6. Label intervention results as conditional forecasts, not causal
   estimates.

## Verified result and why shadow mode is mandatory

On 1,500 held-out synthetic households, Mini's realistic
median-of-scenarios balance MAE was `$270.15`, versus `$614.10` for the
seasonal baseline. Known future events are preserved by deterministic
ledger construction.

The 30-day distress Brier score was `0.02742`, far worse than the GBM
baseline's `0.00142`. Intervention direction accuracy was only `54.8%`
and is an oracle metric that uses the true future to select a scenario.
Calibration, fairness, robustness, privacy, and live shadow evaluation
have not been completed. These are activation blockers, not footnotes.
