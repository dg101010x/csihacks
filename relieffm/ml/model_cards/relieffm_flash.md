# Model Card: ReliefFM Flash

Status: architecture and CPU test path verified locally; CUDA preflight,
training, and evaluation have not run yet. Do not present this model as
having learned weights.

## Architecture

Flash is a 606,144,921-parameter ReliefFM configuration with 1280 hidden
dimensions, 20 attention heads, 3584-wide SwiGLU feed-forward blocks, 19
encoder layers, 11 decoder layers, a 1024-event context, and 128 future
event slots. It retains Mini's coupled baseline/intervention scenario
decoder and deterministic known-event ledger.

Its opt-in V2 path adds QK normalization, 4:1 grouped-query attention,
and masked reconstruction of all seven categorical historical-event
fields plus all nine normalized numeric features. Mini defaults do not
enable this path; the frozen Mini parameter count remains exactly
59,641,666.

## Training safeguards

The Flash path supports BF16, fused AdamW, activation checkpointing,
dynamic sequence trimming, deterministic per-epoch shuffling, gradient
accumulation, periodic full-state recovery, and exact resume metadata.
The GCP pipeline performs real optimizer updates in a CUDA preflight
before long training. Pipeline failures upload available artifacts and
shut the VM down.

## Evaluation policy

Final reporting must use median-of-scenarios as the blind serving metric.
Best-of-scenarios and intervention results selected using ground truth
must remain labeled `ORACLE`. The gradient-boosted distress baseline is
fit on a separate synthetic population, never the evaluation households.
No quality claim belongs in this card until the checkpoint, preflight
report, and evaluation report have been pulled and reviewed.

## Planned hardware

The available upgrade is one full 96 GB RTX PRO 6000 VWS on
`g4-standard-48` in `us-central1-b`. H100 and standard non-VWS RTX PRO
6000 quota requests were denied. The project-wide accelerator quota is
one, so Mini must finish, its artifacts must be pulled, and its stopped
VM must be deleted before Flash is launched.

A separate project is also prepared to request one H100 80 GB
(`a3-highgpu-1g`) through Flex-start. That is the preferred training
target if quota is granted. Its Free Trial billing account must first be
manually activated by the user; no secondary-project GPU has been
provisioned.

## Known limitations

- Synthetic simulator data only; no partner or production data.
- No calibration, fairness, privacy, robustness, or shadow-deployment
  evidence yet.
- Event-set evaluation currently reports count error rather than matched
  precision/recall.
- The intervention encoder's original and modified amount features are
  still degenerate in generated training examples.
- The spec's Nano-to-Mini advancement gate was explicitly overridden.
