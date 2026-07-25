"""GPU preflight for Mini/Flash using real tokenization, losses, and updates.

This intentionally performs optimizer steps rather than forward-only timing:
the first AdamW update materializes optimizer state and is the point at which
an otherwise-promising configuration commonly runs out of memory.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import torch
from torch.optim import AdamW

from ml.relieffm.mini.model import ReliefFMMini
from ml.relieffm.presets import PRESETS
from ml.simulator.population import generate_population
from ml.training.dataset_mini import MiniTensorDataset, collate_mini
from ml.training.mini_losses import compute_mini_loss


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=["mini", "flash"], default="flash")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--n_scenarios", type=int, default=4)
    parser.add_argument("--warmup_steps", type=int, default=1)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--seed", type=int, default=7001)
    parser.add_argument("--activation_checkpointing", action="store_true")
    parser.add_argument("--out_path", type=str, default=None)
    args = parser.parse_args()

    if not torch.cuda.is_available():
        raise RuntimeError("Flash GPU preflight requires a visible CUDA device")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("Flash GPU preflight requires native BF16 support")
    if args.batch_size < 1 or args.steps < 1 or args.warmup_steps < 0:
        raise ValueError("batch_size and steps must be positive; warmup_steps must be nonnegative")

    torch.set_float32_matmul_precision("high")
    config = PRESETS[args.preset]()
    config.use_activation_checkpointing = args.activation_checkpointing
    if config.use_masked_pretraining:
        # Exercise every reconstruction head and materialize its optimizer
        # state; the normal training ratio is restored in the real run.
        config.mask_ratio = 1.0
    records = generate_population(
        max(args.batch_size * 4, 16),
        seed=args.seed,
        as_of=datetime.now(timezone.utc).replace(microsecond=0),
        history_days=120,
        horizon_days=config.forecast_horizon_days,
    )
    dataset = MiniTensorDataset(records, config, seed=args.seed + 1)
    intervention_indices = [
        index for index, example in enumerate(dataset.examples)
        if bool(example["has_intervention"])
    ]
    if not intervention_indices:
        raise RuntimeError("preflight population did not contain a valid intervention example")
    selected = [intervention_indices[0]]
    selected.extend(index for index in range(len(dataset)) if index != intervention_indices[0])
    selected = selected[:args.batch_size]
    batch = collate_mini([dataset[index] for index in selected])
    batch = {key: value.cuda(non_blocking=True) for key, value in batch.items()}

    model = ReliefFMMini(config).cuda().train()
    optimizer = AdamW(model.parameters(), lr=3e-4, weight_decay=0.01, fused=True)

    def update() -> float:
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
            output = model(batch, n_scenarios=args.n_scenarios, include_intervention=True)
            loss = compute_mini_loss(output, batch)["total"]
        if not torch.isfinite(loss):
            raise FloatingPointError(f"preflight produced nonfinite loss: {loss.item()}")
        loss.backward()
        missing_gradients = [
            name for name, parameter in model.named_parameters()
            if parameter.requires_grad
            and parameter.grad is None
            and "reason_factor_head" not in name
        ]
        if missing_gradients:
            raise RuntimeError(
                "preflight did not exercise trainable parameters: "
                + ", ".join(missing_gradients[:10])
            )
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        return float(loss.detach())

    for _ in range(args.warmup_steps):
        update()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    durations: list[float] = []
    losses: list[float] = []
    for _ in range(args.steps):
        started = time.perf_counter()
        losses.append(update())
        torch.cuda.synchronize()
        durations.append(time.perf_counter() - started)

    device_index = torch.cuda.current_device()
    properties = torch.cuda.get_device_properties(device_index)
    peak_allocated = torch.cuda.max_memory_allocated()
    peak_reserved = torch.cuda.max_memory_reserved()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preset": args.preset,
        "num_parameters": model.num_parameters(),
        "torch_version": torch.__version__,
        "device": properties.name,
        "compute_capability": f"{properties.major}.{properties.minor}",
        "total_gpu_memory_bytes": properties.total_memory,
        "peak_allocated_bytes": peak_allocated,
        "peak_reserved_bytes": peak_reserved,
        "reserved_headroom_bytes": properties.total_memory - peak_reserved,
        "batch_size": args.batch_size,
        "n_scenarios": args.n_scenarios,
        "event_tokens": int(batch["event_mask"].shape[1]),
        "known_future_tokens": int(batch["known_mask"].shape[1]),
        "activation_checkpointing": config.use_activation_checkpointing,
        "preflight_mask_ratio": config.mask_ratio,
        "warmup_steps": args.warmup_steps,
        "measured_steps": args.steps,
        "mean_step_seconds": statistics.mean(durations),
        "median_step_seconds": statistics.median(durations),
        "last_loss": losses[-1],
        "passed": True,
    }
    print(json.dumps(report, indent=2))
    if args.out_path:
        out_path = Path(args.out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
