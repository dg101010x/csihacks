# Model Card: ReliefFM Mini

Fields per AGENTS_FM.md §128. Status: **experimental**.

## Why this exists / scope note

This model deliberately skips the spec's own Nano→Mini advancement gate
(§115) — that gate exists to pace a multi-month research program, and
building it wasn't what was asked for here. The explicit instruction was
to build the best architecture achievable in this session and maximize
for a hackathon audience. That tradeoff is stated here plainly rather than
hidden: **this is a from-scratch, single-session, untested-at-scale model.
Nano — smaller, simpler, and empirically validated on a real GCP run
(`ml/model_cards/relieffm_nano.md`) — is the more trustworthy artifact of
the two.** Mini is the ambitious one; its numbers below are real
measurements, not aspirational ones, but there's been far less time to
find and fix problems in it than Nano got.

## Model name / version
`relieffm_mini` / `0.1.0`

## Architecture
Modern-Transformer version of section 20's seven modules
(`ml/relieffm/blocks.py`: RMSNorm, SwiGLU, RoPE, attention via
`torch.nn.functional.scaled_dot_product_attention`) plus two capabilities
Nano doesn't have:

- **Horizon event-set decoder** (§21): `max_event_slots` learned query
  slots predict individual uncertain future events (existence/type/time/
  amount/direction/account/recurrence/obligation-link), trained with a
  DETR-style bipartite matching loss (`ml/training/mini_losses.py`,
  `scipy.optimize.linear_sum_assignment`).
- **Global trajectory latent + coupled intervention sampling** (§22, §31):
  a per-scenario `z ~ N(0,I)` conditions every query in a decode pass;
  baseline and intervention-conditioned forecasts share the same `z`
  values, so `/simulate_intervention` returns a genuinely conditioned
  delta (`services/model_inference/inference_mini.py`) instead of Nano's
  "not modeled" warning.
- **Trajectory heads output point predictions per scenario**, not
  per-day quantile triples (contrast with Nano) — diversity comes from
  varying `z`; daily p10/p50/p90 for the contract response are computed
  empirically across the generated scenario ensemble at inference time.
- **Distress heads** take the learned household embedding *plus*
  legitimate snapshot-derivable engineered features
  (`ml/relieffm/engineered_features.py` — the same features the corrected
  GBM baseline uses, so the two can't drift out of a fair comparison).

## Parameter count
59,641,666 parameters, measured from the trained checkpoint.

## Training objectives
Joint multi-task, one training loop (not the spec's sequential Stage
Three/Four curriculum — a deliberate simplification): trajectory
(best-of-scenarios L1 loss, winner-takes-all selection shared across all
scenario-dependent losses in a batch), event-set matching loss, distress
BCE, accounting consistency, and intervention-delta L1 (masked to
households with a valid synthetic intervention pair). Weights in
`ml/training/mini_losses.py`.

**Winner-takes-all training vs. realistic serving, stated precisely:**
the scenario used for every loss term is chosen *knowing the ground
truth* (lowest trajectory error among the sampled scenarios) — standard
practice for training diverse/multi-modal generators, but it means
training-time losses are not directly comparable to blind-inference
error. `ml/evaluation/run_eval_mini.py` reports both an oracle
(ground-truth-selected, labeled `_ORACLE`) number and a realistic
median-of-scenarios number for trajectory metrics; don't read the oracle
numbers as achievable in a live forecast where the true future is
unknown.

## Training data summary
Synthetic only (ReliefSim, Tier Two per §34): 25,000 households and
3,736,473 events, seed 1, with 20,035/2,516/2,449
train/validation/test households. Trained for 12 epochs (7,524 optimizer
steps) on one NVIDIA L4 in 7,281.9 seconds. No non-finite steps were
skipped. Dataset version `relief_data_0.1.0`. See `data_card.md`.

## Intended use
Same as Nano's: research and internal shadow evaluation, not production
financial decisions. `/simulate_intervention` is the one genuinely new
capability worth demoing — real coupled-sampling intervention-conditioned
forecasts.

## Prohibited use
Identical to Nano's — AGENTS_FM.md §131, verbatim: credit approval/denial,
interest rate or credit limit changes, insurance cancellation, contractual
term changes, transaction execution, legal eligibility determination,
inferring protected traits, adverse action reasons, replacing provider
policy validation.

## Supported horizons / currencies / products
Same pattern as Nano: one fixed horizon this checkpoint was trained for
(see config below), USD only, the same ten `ObligationType` values.

## Primary metrics
Evaluation used 1,500 independently generated synthetic households,
16 scenarios, and the fixed 60-day horizon:

- Realistic median-of-scenarios balance MAE: **$270.15**, versus
  **$614.10** for the seasonal baseline (2.27x lower error).
- Median minimum-balance error: **$64.53**, versus **$410.39** for the
  seasonal baseline.
- 30-day distress Brier: **0.02742**, versus **0.00142** for the GBM
  baseline. Mini does not win this task.
- 30-day distress ECE: **0.01389**; false-reassurance rate: **0.00919**.
- Event-count MAE: **6.542** events. This is not matched event
  precision/recall.
- Intervention end-of-horizon delta MAE: **$7.37 ORACLE**, versus
  **$57.73** for predicting zero effect. Direction accuracy:
  **54.8% ORACLE**, only slightly above chance.

`ORACLE` means the scenario was selected using the true future. It is not
a deployable blind-inference result. Exact machine-readable results are
in `runs/mini_20260725_122238/eval_report.json` and the release pointer is
`integration/mini_20260725_122238.release.json`.

## Calibration / Fairness / Robustness results
Not run — identical situation to Nano, unchanged by this upgrade.

## Known limitations
- **Everything in this file is from a single session with no time for the
  multi-round bug-hunting Nano got.** Two real bugs were already found and
  fixed during development (an intervention-delta indexing bug that made
  every delta target exactly zero, and the GBM baseline's parameter
  leakage, shared with Nano's card) — there is no reason to assume those
  were the last two.
- **Intervention encoder's amount features are degenerate.** Training data
  (`ml/datasets/compile.py`'s `InterventionExample`) sets
  `original_amount_cents == modified_amount_cents` for every example (both
  equal the obligation's scheduled amount), so the amount-delta feature
  fed to the model is always zero in training. The model differentiates
  interventions mainly by action type, dates, and added cost — not by how
  large the actual monetary change is. Inference-time feature construction
  intentionally mirrors this (see `inference_mini.py`'s docstring) to
  avoid a train/inference mismatch, rather than one-sidedly "fixing" only
  one side.
- **Event-set evaluation is unmatched.** `run_eval_mini.py` reports
  predicted-vs-true event *counts* (existence threshold 0.5, averaged over
  scenarios), not a proper matched precision/recall — that needs
  per-scenario re-matching at eval time, which wasn't built this session.
- **No Stage One self-supervised pretraining**, same as Nano.
- **Single L4 GPU, not the "best" available.** A100 and multi-L4 quota
  increase requests were both auto-denied (this project's account tier
  caps at 1 GPU) — see `infra/gcp/config.sh`. Compute budget, not
  architecture, was the binding constraint on model/data scale.
- **No calibration, fairness, robustness, or privacy testing.**
- **No shadow deployment**, no live Plan Two.

## Privacy considerations
Training data is 100% synthetic. No real household data used.

## Serving requirements
`services/model_inference` (same FastAPI service as Nano — dispatches
automatically based on `checkpoint_meta.json`'s `model_name`),
`RELIEFFM_CHECKPOINT_DIR` pointing at this checkpoint. Meaningfully more
compute per request than Nano (bigger model, decoder runs twice for
intervention requests, `n_scenarios` generative samples instead of one
parametric quantile head). The held-out evaluation measured 0.0511
seconds per forward batch on the training L4 at 16 scenarios. A local CPU
smoke request with two scenarios took 0.083 seconds after a 0.443-second
load, but this is not a production concurrency or tail-latency benchmark.

## Fallback behavior
None server-side, same as Nano — Plan Two's deterministic provider is the
real fallback.

## Responsible owner
Plan One workstream. No named individual owner assigned this session.

## Explicit gate status
The §115 Nano→Mini gate was not evaluated for this model because it does
not apply to it — that gate governs *whether to start building Mini*, and
Mini was already built here on explicit instruction, overriding it. No
claim is made that this model meets any of the spec's advancement,
activation, or foundation-model-naming criteria (§115–118).
