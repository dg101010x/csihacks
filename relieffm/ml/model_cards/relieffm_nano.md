# Model Card: ReliefFM Nano

Fields per AGENTS_FM.md §128. Status: **experimental** (not `shadow` yet — no
live Plan Two integration exists to shadow against this session).

## Model name / version
`relieffm_nano` / `0.1.0`

## Architecture
Household Context Encoder (1 layer) + Historical Event Encoder (2 layers,
bidirectional) + Known-Future Encoder (1 layer) → Context Fusion Layer →
parallel horizon decoder (2 layers, one learned query per forecast day) →
four quantile trajectory heads (inflow / essential outflow / discretionary
outflow / balance residual) + distress hazard heads (3 risks × 3 horizons)
+ a diagnostic (untrained) reason-factor head. Full module-by-module
mapping to AGENTS_FM.md §20 is in `ml/relieffm/`'s per-module docstrings.

## Parameter count
**6,516,255** (measured — spec's 8M–15M is a target range, not a
requirement; this implementation's layer allocation across three encoder
modules plus modest vocab sizes lands just under it).

## Training objectives
Pinball (quantile) loss on the four uncertain-component trajectory heads +
BCE on distress heads + an accounting-consistency term between the
balance-residual head and the balance implied by cumsum(inflow − outflows)
from the other three heads. Weights renormalized from AGENTS_FM.md §60's
trajectory/distress/accounting terms (0.46 / 0.38 / 0.15).

## Training data summary
Synthetic only (ReliefSim, Tier Two per §34). See `data_card.md`.

**Actual training run** (`runs/nano_20260725_110729`, trained on GCP:
`g2-standard-4`, 1× NVIDIA L4, `us-east1-b`):
- 30,000 households, 3,349,178 events, generated in 204s
- Split: 24,048 train / 3,007 val / 2,945 test (household-level, §47)
- `dataset_version`: `relief_data_0.1.0`
- 30 epochs, batch size 128, 5,640 steps, 884s (~14.7 min) training time on GPU
- Python 3.10.12, PyTorch 2.9.1+cu129
- `git_commit`: unknown (no commits made in this repo during the session)
- Final val loss: total 0.127, trajectory 0.182, distress 0.111, accounting 0.006
  (down from 0.257 / 0.280 / 0.330 / 0.019 at the first validation pass —
  steady convergence, no divergence, no non-finite steps skipped)

## Intended use
Household cash-flow trajectory forecasting (uncertain component only —
known obligations/paychecks are deterministic, section 23) for research
and internal shadow evaluation. Not for production financial decisions.

## Prohibited use
Credit approval, credit denial, interest rate setting, credit limit
changes, insurance cancellation, contractual term changes, transaction
execution, legal eligibility determination, inferring protected traits,
producing adverse action reasons, replacing provider policy validation
(AGENTS_FM.md §131, verbatim).

## Supported horizons
30 days only (Nano was trained and tokenized for a fixed 30-day horizon;
the metadata endpoint reports this honestly rather than the spec's
illustrative `[7, 14, 30]`, since this checkpoint cannot actually serve
7- or 14-day requests as a *different* horizon — those numbers are
sub-horizons of the single 30-day distress heads, not separate forecast
lengths).

## Supported currencies
USD only (`relief_contracts` rejects anything else).

## Supported products
Rent, mortgage, auto loan, personal loan, credit card minimum, insurance
premium, utility, subscription, BNPL, medical payment plan (all ten
`ObligationType` values the simulator generates).

## Primary metrics
Measured on 1,500 freshly-generated held-out households (seed 99991, distinct
from the training seed) — full numbers in `runs/nano_20260725_110729/eval_report.json`.

**Trajectory** (Nano vs. seasonal-median baseline, both predicting the same
uncertain-component residual on top of the identical deterministic known
component):
| metric | Nano | seasonal baseline |
|---|---|---|
| balance MAE | $69.90 | $190.31 |
| min-balance error | $41.97 | $87.21 |
| end-of-horizon balance error | $141.25 | $510.70 |
| pinball loss (balance residual) | 0.279 | — (baseline has no quantiles) |

Nano beats the seasonal baseline by roughly 2.7-3.6x across all three
balance error metrics — the clearest positive result from this run.

**Distress, 30-day negative-balance risk** (Nano vs. gradient-boosted-trees
baseline; base rate 51.7% positive in this eval population):
| metric | Nano | GBM baseline |
|---|---|---|
| Brier score | 0.0407 | **0.0017** |
| ECE | 0.0274 | **0.0139** |
| false reassurance rate | **1.0%** | not measured |

**Negative result, reported per §164:** the GBM baseline clearly
out-calibrates Nano on 30-day distress classification. This is plausible,
not a bug — distress-at-30-days is close to a tabular classification
problem, and GBM gets hand-engineered liquidity/recurrence features
(§79) purpose-built for exactly this target, while Nano's distress head
is a small MLP sharing a representation trained jointly across four other
objectives. Nano's one clear edge is a low false-reassurance rate (rarely
calls an actually-distressed household safe), which matters most per §86
but doesn't overcome the Brier/ECE gap.

**Correction (found and fixed after this card was first written):** the
GBM baseline originally scored Brier 0.0011 here, but its feature set was
leaking `HouseholdParams` — the simulator's hidden generative parameters
(`income_reliability`, `debt_burden`, `shock_frequency`, etc.), which a
real system would never observe. `ml/baselines/gradient_boosted.py` was
rewritten to use only snapshot-derivable features; the corrected Brier
above (0.0017) is the honest number. The GBM still wins clearly even
without the leak — this is a real gap, not an artifact.

## Calibration results
Not run this session — `ml/calibration/temperature_scaling.py` exists but
no fitted temperature is loaded by the inference service.
`calibration_version` is reported as `calibration_uncalibrated_0.0.0`.

## Fairness results
Not run. No audit attributes exist in the synthetic population (there are
no protected-trait proxies deliberately encoded, but this has not been
tested — see §91). **Not evaluated, not claimed.**

## Robustness results
Not run. Section 90's corruption battery (missing/duplicate transactions,
stale balances, etc.) is not implemented this session. The inference
service does emit basic completeness/freshness/sparsity warnings
(`services/model_inference/inference.py`), which is a smaller thing than
robustness testing.

## Known limitations
- **No Stage One self-supervised pretraining.** Trained end-to-end
  supervised only (Stage Two, §63). Hypothesis Five ("pretraining beats
  training from scratch") is **not evaluated** by this checkpoint.
- **No horizon event-set decoder.** Nano predicts aggregate daily quantile
  series, not individual future events — by design (§19.1), not a cut
  corner, but it does mean event-level metrics (§84) don't apply.
- **No intervention-conditioned forecasting.** `/simulate_intervention`
  applies the intervention deterministically to known events and returns
  an *unconditioned* uncertain-component forecast, with an explicit
  warning to that effect. Real intervention-conditioned forecasting is
  Mini-scope (§19.2).
- **No contrastive objective, no masked-field objective.**
- **Single dynamic ledger account per household.** All cash-flow events
  settle against one checking-equivalent account; savings/credit-card/loan
  accounts are static context tokens, not part of the ledger (see
  `ml/simulator/population.py`'s docstring).
- **Synthetic data only.** No public or partner dataset adapter was run.
  Every claim in this card is about ReliefSim's synthetic population, not
  real households — §34's boundary applies in full.
- **No calibration, fairness, robustness, or privacy testing performed.**
- **No shadow deployment.** There is no live Plan Two to shadow against.
- **`run_eval.py` doesn't move the model/batches to the GPU device**, so
  the measured `avg_forward_seconds_per_batch` (1.13s) is CPU inference on
  the training VM, not a GPU latency number — don't read it as a serving
  latency estimate (§126 explicitly wants benchmarked, not claimed,
  numbers; this one just wasn't benchmarked correctly).
- **Distress head underperforms a GBM baseline** on 30-day negative-balance
  Brier/ECE (see Primary metrics) — flagged, not fixed, this session.
- **Overconfident on sparse/out-of-distribution history.** Spot-checked
  against realistic simulator households (~100 historical events, matching
  training distribution), the trained checkpoint separates distressed vs.
  not-distressed correctly with high confidence (predicted probabilities
  of 0.0004, 0.99991, 0.00005 for three fresh households whose true 30-day
  labels were False/True/False). Against `relief_contracts.fixtures`'
  deliberately minimal snapshot (2 historical events, by design — it's a
  contract-testing fixture, not a realistic household), it predicts 99.98%
  distress regardless of the household's actual healthy balance. The
  service does emit a `sparse event history` warning in that case, but the
  reported `confidence` field only drops to 0.7 — nowhere near enough to
  signal "this probability is close to meaningless." This is exactly the
  kind of gap section 90's robustness battery exists to catch and section
  91's sparse-history fairness check would quantify; neither ran this
  session, so treat sparse-history distress outputs as unreliable until
  they do.

## Privacy considerations
Training data is 100% synthetic (ReliefSim). No real household data was
used or could have been memorized.

## Serving requirements
`services/model_inference` (FastAPI), one L4-class GPU or CPU for
interactive-latency inference at Nano's size, `RELIEFFM_CHECKPOINT_DIR`
pointing at a `checkpoint/` directory containing `model.safetensors` +
`checkpoint_meta.json`.

## Fallback behavior
None implemented server-side — that's Plan Two's deterministic-provider
responsibility (§18, §125). This service returns HTTP error codes on
invalid input or internal validation failure; it never returns a partial
forecast as if it were complete (§122).

## Responsible owner
Plan One workstream (this repository). No named individual owner assigned
this session.

## Section 115 gate status (Nano → Mini)
| criterion | result |
|---|---|
| Beats the seasonal baseline on uncertain daily balance forecasting | **met** |
| Beats gradient boosted trees on at least one sequence dependent risk task | **not met** (GBM wins on 30d distress Brier/ECE) |
| Preserves every known future event | **met** (structural, verified in `run_eval.py` and `tests/test_dataset_compiler.py`) |
| Passes contract tests | met (21/21 pytest, see Stage Zero section) |
| Produces no unreconciled balances after Plan Two validation | not evaluated — no live Plan Two |
| Serves within the integration latency budget | not evaluated — no budget defined by Plan Two yet |

`overall_met` is hard-coded `False` in `run_eval.py` regardless of the
measured metrics, because two of the six criteria can't be evaluated
without an actual Plan Two integration, and one of the four that *can* be
measured is not met. **This model has not cleared the Mini-eligibility
gate and should not be used as justification to start Mini.** The honest
next step, per §115, is improving the distress head (larger/dedicated
capacity, or blending with a GBM-style feature set) before re-running this
gate — not scaling up to Mini.
