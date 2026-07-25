# ReliefFM — Project Context & Handoff

Last updated: 2026-07-25 15:20 PDT. **This file exists so you (or a
fresh Claude Code session on a different machine) can pick this up cold.**
Read this whole file before touching anything. Then paste the "Handoff
Prompt" section at the very bottom into a new session.

## What this is

`$HOME/Projects/csihacks/AGENTS_FM.md` is a huge spec for
"ReliefFM" — an obligation-aware financial forecasting model (Plan One of
a two-part hackathon project; a partner is separately building "Plan Two,"
the consumer/provider app, on a different machine). This `relieffm/`
directory is a from-scratch implementation of as much of that spec as is
achievable, built incrementally and honestly in one long session, with
real GCP GPU training runs (not simulated/pretend).

**Repo**: `$HOME/Projects/csihacks` (git repo, main branch).
`relieffm/` is untracked so far — nothing has been committed. `AGENTS_FM.md`
is also untracked.

**GCP project**: `cerebrum-research`, billing enabled, with the primary
training account authenticated. The quota-contact email is stored in GCP,
not in this public repository.

**Secondary GCP environment**: credentials are isolated under
`$HOME/.config/gcloud-relieffm-credit2` for the secondary billing account,
project
`project-338dfd29-72ec-41af-8c7`. Always prefix its commands with
`CLOUDSDK_CONFIG=$HOME/.config/gcloud-relieffm-credit2`;
the default gcloud configuration must remain on the primary Mini project.
Compute, Vertex AI, Cloud Run, Artifact Registry, Cloud Quotas, Cloud
Billing, and Budget APIs are enabled. A
project-scoped `$250` gross-spend budget named `ReliefFM credit guard`
exists with 25/50/75/90/100% actual-spend alerts and a 75% forecast
alert. The user activated billing and the billing account is open.
Nevertheless, every GPU request is currently provider-blocked for
`NOT_ENOUGH_USAGE_HISTORY`: Compute aggregate, H100, and RTX PRO 6000;
Vertex AI H100 and RTX PRO 6000; and Cloud Run L4 were all granted zero.
Cloud Run's RTX PRO 6000 path also requires 80 GiB regional memory, while
this project is capped at 40 GiB; the minimum 80 GiB request was denied.
The documented first-deployment Cloud Run L4 auto-grant did not apply to
this organization. No VM, GPU job, or paid accelerator has been created.
The only secondary resources are the regional results bucket
`gs://project-338dfd29-72ec-41af-8c7-relieffm`, an empty Artifact Registry
repository, and the least-privilege `relieffm-cloud-run` service account.
At the user's request, legitimate billing history was created with two
bounded CPU validations on 2026-07-25: an `e2-standard-8` Compute VM ran
the 28-test suite and trained a one-epoch 6.5M-parameter Nano checkpoint,
then uploaded 97 MB of evidence under
`history/compute_cpu_history_20260725_1438/` and was deleted; a Cloud Run
8-vCPU/32-GiB job ran the same tests and Nano training successfully in
6m17s. The minimum Compute aggregate/H100, Cloud Run L4, and Vertex H100
preferences were resubmitted afterward with this evidence and were still
granted zero. Eligibility remained `NOT_ENOUGH_USAGE_HISTORY`, so do not
burn more CPU merely to increase volume—the provider also considers the
length of billing history and does not disclose its approval threshold.

## Model lineage (three models, escalating scope)

### 1. ReliefFM Nano — DONE, trained, evaluated, real results
- ~6.5M params. Plain `nn.TransformerEncoder`/`Decoder` (not the modern
  blocks below). Predicts daily balance/inflow/outflow **quantiles**
  (p10/p50/p90) directly, no scenario sampling, no event-set decoder, no
  real intervention conditioning.
- Trained on GCP: `g2-standard-4` (1x L4), `us-east1-b`, 30,000
  households, 30 epochs, ~15 min GPU time. Checkpoint at
  `runs/nano_20260725_110729/`.
- **Real, reported results**: beats a seasonal-median baseline on balance
  forecasting by 2.7-3.6x. Loses to a gradient-boosted-trees baseline on
  30-day distress classification (Brier 0.041 vs 0.0017 after a leakage
  fix — see below). Full writeup: `ml/model_cards/relieffm_nano.md`.
- Two real bugs were found and fixed on this model during development:
  1. Checking-account starting balance was drawn from
     `lognormal(mean=7.2)` (median ~$13, should've been ~$1000) — pushed
     ~99% of synthetic households into apparent distress. Fixed in
     `ml/simulator/accounts.py`.
  2. Rent/mortgage sizing used a per-pay-period income figure as if it
     were monthly income. Fixed in `ml/simulator/obligations.py`.

### 2. ReliefFM Mini — DONE, trained and evaluated
- ~59.6M params. This is where the real architecture upgrades live:
  RMSNorm/SwiGLU/RoPE/SDPA modern Transformer blocks
  (`ml/relieffm/blocks.py`), a horizon **event-set decoder** (DETR-style,
  predicts individual future events with Hungarian matching loss), a
  global trajectory latent `z` per scenario (real generative diversity,
  not a post-hoc trick), and **real intervention-conditioned forecasting**
  — coupled baseline/intervention decoding sharing the same `z`
  (`/simulate_intervention` actually works now, unlike Nano's).
- Trained on GCP: `g2-standard-4` (1x L4), `us-east1-b`, instance name
  `relieffm-train`, 25,000 households, 12 epochs, batch 32,
  `n_scenarios_train=4`. The completed run is
  `mini_20260725_122238`: 7,524 optimizer steps, 7,281.9 seconds of
  training, and zero skipped non-finite steps. The instance self-stopped
  at 14:42 PDT and was deleted after artifact verification at 15:17 PDT.
- **A real bug was found and fixed during eval-script development**: the
  intervention-delta target was reading from the wrong slice of the
  balance array (history window instead of the forecast horizon),
  producing all-zero targets. Fixed in
  `ml/datasets/compile.py`'s `household_record_to_intervention_example`
  — there's a regression test for this in `tests/test_mini.py`.
- **Another bug**: bf16 mixed-precision training crashed on
  `binary_cross_entropy` dtype mismatch (model output bf16, batch targets
  fp32). Fixed via `ml/training/mini_losses.py`'s `_to_fp32` helper.
- Real evaluation on 1,500 held-out synthetic households:
  median-of-scenarios balance MAE $270.15 versus $614.10 for the seasonal
  baseline; 30-day distress Brier 0.02742 versus 0.00142 for the GBM
  baseline; oracle intervention direction accuracy 54.8%. The trajectory
  result is good, while distress and intervention evidence are not strong
  enough for activation. See `ml/model_cards/relieffm_mini.md`.
- All 804 MiB of uploaded run artifacts were pulled locally and verified
  by exact byte size. Serving weights SHA-256:
  `1547b75758b670f7e8cf233a34d0dac91bcdaf4b59991e148f39c0cee247e00c`.
  The source of truth remains
  `gs://cerebrum-research-relieffm/runs/mini_20260725_122238/`.
- The Plan Two handoff is in `integration/`: release manifest, contract
  schemas, OpenAPI, real request/response fixtures, serving steps, shadow
  policy, and deterministic-fallback requirements.

### 3. ReliefFM Flash — CODE READY, NOT YET TRAINED
- Same top-level `ReliefFMMini` composition, using opt-in V2 blocks behind
  `MiniConfig` feature flags so the Mini checkpoint remains loadable.
- **606,144,921 parameters measured locally**: hidden=1280, 20 attention
  heads (64 dimensions/head), FFN=3584, 19 encoder layers (4 context + 11
  history + 4 known-future), 11 decoder layers, context_events=1024, 128
  event slots.
- Three genuine architecture upgrades over Mini, all opt-in via new
  `MiniConfig` fields defaulting to OFF (so Mini's already-trained
  checkpoint stays loadable — see "Critical constraint" below):
  1. **QK-Norm** (`use_qk_norm=True`) — RMSNorm on Q/K before attention,
     stability at 10x the parameter scale.
  2. **Grouped-Query Attention** (`n_kv_heads=5` out of 20 heads) — a 4:1
     query-to-KV ratio that cuts KV projection and attention memory.
  3. **Masked event reconstruction** (`use_masked_pretraining=True`) — a
     genuine self-supervised auxiliary objective (spec's Objective One,
     §49) over all seven categorical fields and all nine numeric features.
     Training-time only; inference never masks real history.
- Flash training also has dynamic padding removal, non-reentrant
  activation checkpointing, BF16, fused AdamW, deterministic epoch
  shuffling, gradient accumulation, atomic rolling full-state recovery,
  resumable data timestamps/sample order, and crash-time GCS upload plus
  automatic VM shutdown.
- Cloud Run's one-hour GPU-task limit is supported without corrupting the
  learning-rate schedule: `train_mini.py --stop_after_steps` advances a
  bounded number of additional optimizer steps, saves exact recovery
  state, and exits before final evaluation. `cloud_run_worker.py`
  downloads that state, runs the next chunk, uploads it, and lets a
  sequential multi-task job continue until final evaluation. This path is
  code-complete and locally covered by the 28-test suite, but no Cloud Run
  GPU was available for its required real preflight.
- `ml/training/benchmark_mini.py` now performs real forward/backward/fused
  optimizer updates before a long run. `run_pipeline.sh` invokes this
  preflight automatically and aborts safely if the chosen microbatch does
  not fit.
- All three verified end-to-end locally (forward + loss + backward, no
  NaN, all expected gradients present) before spending any GPU time.
  Also re-verified the safety constraint itself:
  `ReliefFMMini(mini_config()).num_parameters() == 59_641_666` still holds
  exactly after all these changes — Mini's checkpoint is safe.
- **GPU plan**: the project has one RTX PRO 6000 **VWS** quota granted in
  `us-central1`. `g4-standard-48` + `nvidia-rtx-pro-6000-vws` is visible
  in `us-central1-b`: one full 96 GB RTX PRO 6000, 48 vCPU, 180 GiB host
  memory. This is four times the VRAM of the current quarter-card
  `g4-standard-12`. **Not yet benchmarked or provisioned.** Standard
  non-VWS RTX PRO 6000 and H100 quota requests were submitted and denied.
  The project's aggregate GPU quota
  (`GPUS-ALL-REGIONS-per-project`) is hard-capped at 1 (A100 and
  multi-L4 increase requests were both auto-denied — this is an
  account-tier limit, not fixable via CLI), so Flash can't run
  concurrently with Mini. **Wait for Mini's VM to be torn down before
  launching Flash** (or the `gcloud compute instances create` call will
  fail on quota).
- Next steps: (1) finish the Plan Two shadow integration; (2) launch with
  `GPU_PROFILE=g4-full-vws INSTANCE_NAME=relieffm-flash-train
  MODEL_TARGET=mini MODEL_PRESET=flash`; (3) inspect the automatically
  uploaded `preflight.json`; (4) only keep the long run if preflight
  memory, speed, and finite-loss checks pass; (5) evaluate Flash and
  update `ml/model_cards/relieffm_flash.md` with real results.
- The stronger parallel option in the secondary project is currently
  blocked by provider eligibility, not by code or billing activation.
  `GPU_PROFILE=h100` still targets one `a3-highgpu-1g` H100 80 GB through
  Flex-start at about `$4.79/hour`, with a provider-enforced 12-hour
  maximum and automatic deletion. `g4-full-flex` is the 96 GB RTX PRO
  6000 fallback. Both Compute requests and the equivalent Vertex AI
  requests were submitted after billing activation and immediately
  denied. Cloud Run was also exhausted as an independent path: RTX was
  blocked by the 40 GiB memory ceiling and L4 remained at zero quota.
  Do not claim the secondary Flash run is launched until one of these
  effective quotas is nonzero and the full-update preflight passes.

## Critical constraint — read before touching model code again

**Never modify `ml/relieffm/blocks.py`'s existing classes
(`SelfAttention`, `CrossAttention`, `EncoderBlock`, `DecoderBlock`,
`EncoderStack`, `DecoderStack`) or anything Mini's already-training
architecture depends on with its default config.** Mini's checkpoint (in
progress or finished) was built by `ReliefFMMini(mini_config())` using
that exact code. If those classes change shape/parameter names — even
"improving" them — `load_state_dict` breaks on Mini's checkpoint forever.

The pattern used for Flash's upgrades: add NEW classes/parameters,
gate everything behind new `MiniConfig` fields that default to values
reproducing Mini's exact current behavior. Verify safety by asserting
`ReliefFMMini(mini_config()).num_parameters() == 59_641_666` after any
change to `ml/relieffm/blocks.py`, `ml/relieffm/mini/*.py`, or
`ml/relieffm/config.py` — that number must never change.

## How to check GCP status

```bash
gcloud compute instances list --project=cerebrum-research
gcloud compute instances get-serial-port-output relieffm-train --zone=us-east1-b --project=cerebrum-research | tail -50
gcloud storage ls gs://cerebrum-research-relieffm/runs/
```

**The serial-console log can look stalled when the job is actually fine.**
Python block-buffers stdout when piped through `tee` (which
`run_pipeline.sh` does), so the visible log can lag several minutes behind
real progress — this happened during Mini's run: the log sat at step 440
for 5+ minutes and looked hung. Don't kill the VM on a quiet log alone —
confirm first:

```bash
gcloud compute ssh <instance-name> --zone=<zone> --project=cerebrum-research \
  --command="nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv; ps aux | grep train_mini | grep -v grep"
```

If GPU utilization is high and the python process shows real CPU time
accumulating, it's fine — just wait for the next buffer flush. **This is
now fixed for future runs** — `run_pipeline.sh` sets `PYTHONUNBUFFERED=1`
— but Mini's already-launched run started before that fix, so its log
will keep lagging until it finishes.

The training VM (`relieffm-train`, or `relieffm-flash-train` if you name
it that way for Flash) **self-shuts-down** when its pipeline finishes
(stops billing) but isn't deleted — always run
`INSTANCE_NAME=<name> ZONE=<zone> infra/gcp/teardown.sh` after pulling
results, both to free the GPU quota slot and to stop disk billing.

Future VMs now trap any pipeline failure, upload the run directory and
pipeline log, and shut down automatically. Still verify the instance is
`TERMINATED` after any failure and delete it after artifacts are pulled;
the currently running Mini VM predates this safeguard.

## Directory map

```
relieffm/
  context.md                    <- you are here
  README.md                     <- quickstart, layout overview
  packages/relief_contracts/    shared request/response schemas (Plan Two's contract)
  ml/simulator/                 ReliefSim: synthetic household population generator
  ml/datasets/compile.py        simulator output -> canonical snapshot + all target types
  ml/relieffm/
    blocks.py                    modern Transformer blocks (V1 = Mini/frozen, V2 = Flash upgrades)
    config.py                    NanoConfig, MiniConfig (Flash is a MiniConfig instance)
    presets.py                   mini_config() / flash_config() factories
    engineered_features.py       legitimate (snapshot-derivable) distress features -- shared by
                                  the GBM baseline and Mini/Flash's distress head, so they can't
                                  drift out of a fair comparison
    tokenize.py                  Nano's tokenizer (Mini/Flash reuse it via duck typing)
    mini/                        Mini/Flash-specific modules (encoders, decoder, heads, model.py)
  ml/training/
    train.py / losses.py          Nano training
    train_mini.py / mini_losses.py  Mini/Flash training (--preset mini|flash)
    dataset.py / dataset_mini.py   tensor datasets + dynamic Mini/Flash collation
    benchmark_mini.py              full-update CUDA memory/throughput preflight
  ml/baselines/gradient_boosted.py  GBM baseline (uses engineered_features.py, no leakage)
  ml/evaluation/run_eval.py / run_eval_mini.py   evaluation scripts, both device-aware (CUDA if available)
  ml/model_cards/                relieffm_nano.md, relieffm_mini.md, relieffm_flash.md, data_card.md
  services/model_inference/       FastAPI service, dispatches Nano vs Mini/Flash automatically
                                  based on checkpoint_meta.json's model_name
  infra/gcp/                      gcloud-CLI-only provisioning: config.sh, setup.sh, train_vm.sh,
                                  run_pipeline.sh (runs ON the VM), teardown.sh
  tests/                          pytest suite, 28 tests, all passing
```

## Known limitations (disclosed, not hidden)

Full lists are in the model cards, but the headlines:
- No Stage One self-supervised pretraining for Nano or Mini (Flash gets
  masked reconstruction, but it's untested at scale — GPU time not spent
  on it yet).
- No calibration, fairness, robustness, or privacy testing performed for
  any model.
- No shadow deployment — there's no live Plan Two to shadow against.
- Nano's `/simulate_intervention` doesn't actually condition on the
  intervention (says so in its warnings). Mini/Flash's does, for real,
  via coupled scenario sampling.
- Mini/Flash's event-set evaluation is unmatched (predicted vs true event
  *counts*, not proper precision/recall).
- Mini/Flash's intervention encoder has degenerate amount features
  (original == modified in training data) — action type/dates/cost carry
  the signal, not amount deltas. Documented in the model card, not fixed
  (would need more simulator plumbing).
- The §115 Nano→Mini advancement gate from the spec was deliberately
  skipped for Mini/Flash — explicit user instruction to build the best
  architecture for a hackathon audience, overriding the spec's own
  research-pacing discipline. Stated plainly in the model cards.
- The GBM baseline now trains on an independently generated population;
  older reports that fit and scored it on the same households should not
  be used for final comparisons.

## Session history highlights (why decisions were made)

- Started as a disciplined, spec-following build of just Nano (see
  git-free session history — no commits made, everything is still
  working-tree only). Nano was fully built, tested (21 tests), and
  trained successfully on GCP with honest reporting of a real weakness
  (distress head loses to GBM baseline).
- User then said "fix all of this, best architecture, latest components,
  more GPUs, bigger data, maximize for judges" — this triggered building
  Mini (event-set decoder + intervention conditioning + modern blocks),
  overriding the spec's own advancement-gate discipline explicitly and
  on the record.
- GPU quota was a real fight: L4 quota needed a `gcloud alpha quotas
  preferences create` request (auto-approved instantly once submitted
  correctly — the trick was the `--email` flag is required for any
  increase, and `GPUS-ALL-REGIONS-per-project` is a *separate* aggregate
  cap from the per-type/per-region ones). A100 and multi-L4 were both
  auto-denied — hard account-tier ceiling of 1 GPU total. RTX PRO 6000
  quota (a different accelerator family, `g4-standard-12` machine type)
  was granted for a future Flash run, but shares the same aggregate-1
  ceiling, so it can't run alongside Mini.
- Then user asked about further architecture upgrades for Flash
  specifically ("novelty and effectiveness") — resulted in QK-Norm, GQA,
  and masked reconstruction, all designed additively/opt-in specifically
  to not risk Mini's in-flight checkpoint.
- Mini's log appeared to stall for 5+ minutes mid-run (user flagged it).
  SSH + `nvidia-smi`/`ps` confirmed the GPU was at 92% utilization and the
  process was actively burning CPU the whole time — it was stdout
  buffering (Python block-buffers when piped through `tee`), not a hang.
  Fixed for future runs via `PYTHONUNBUFFERED=1` in `run_pipeline.sh`.
  Lesson: don't kill a VM on a quiet log alone, verify via SSH first.

---

## Handoff Prompt

**Paste everything below this line into a fresh Claude Code session
(any workstation) to continue this project.**

```
I'm continuing work on ReliefFM, a from-scratch implementation of the spec
in AGENTS_FM.md (repo root: csihacks/, project dir: csihacks/relieffm/).
Read csihacks/relieffm/context.md in full first -- it has the complete
project state, GCP account details, what's done vs in-progress, and a
critical constraint about not breaking Mini's already-trained checkpoint
architecture. Then check GCP status (instructions in that file) to see
where the Mini training run and/or Flash benchmark/training actually
landed, and pick up from there. Ask me if anything in context.md seems
stale or contradicts what you find on GCP -- don't just assume the file
is current, verify against actual GCP/repo state first.
```
