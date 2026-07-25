"""Stage Two (section 63): Nano trajectory + distress training.

Runs Stage Zero implicitly (every batch is a snapshot -> tensors ->
ForecastResponseV1-shaped output round trip) and Stage Two explicitly. No
Stage One self-supervised pretraining this session — see the model card.

    python -m ml.training.train --n_households 5000 --epochs 6 --out_dir runs/nano_v1
"""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import torch
from accelerate import Accelerator
from safetensors.torch import save_file
from torch.optim import AdamW
from torch.utils.data import DataLoader

from ml.datasets.splits import assign_splits
from ml.datasets.writer import write_dataset, DATASET_VERSION
from ml.relieffm.config import NanoConfig
from ml.relieffm.model import ReliefFMNano
from ml.simulator.population import generate_population
from ml.training.dataset import HouseholdTensorDataset, collate
from ml.training.losses import compute_loss

CALIBRATION_VERSION = "calibration_uncalibrated_0.0.0"  # section 67 not run this session


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--n_households", type=int, default=5000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--history_days", type=int, default=90)
    p.add_argument("--horizon_days", type=int, default=30)
    p.add_argument("--epochs", type=int, default=6)
    p.add_argument("--batch_size", type=int, default=64)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=0.01)
    p.add_argument("--out_dir", type=str, default="runs/nano_v1")
    p.add_argument("--eval_every_steps", type=int, default=200)
    p.add_argument("--log_every_steps", type=int, default=20)
    p.add_argument("--write_dataset", action="store_true", default=True)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    accelerator = Accelerator()
    config = NanoConfig(forecast_horizon_days=args.horizon_days)

    as_of = datetime.now(timezone.utc).replace(microsecond=0)
    if accelerator.is_main_process:
        print(f"Generating {args.n_households} synthetic households (seed={args.seed})...")
    t0 = time.time()
    records = generate_population(
        args.n_households, seed=args.seed, as_of=as_of,
        history_days=args.history_days, horizon_days=args.horizon_days,
    )
    gen_seconds = time.time() - t0

    splits = assign_splits([r.params.household_id for r in records])
    train_records = [r for r in records if splits[r.params.household_id] == "train"]
    val_records = [r for r in records if splits[r.params.household_id] == "val"]

    manifest = {}
    if args.write_dataset and accelerator.is_main_process:
        manifest = write_dataset(records, str(out_dir / "dataset"), seed=args.seed)

    if accelerator.is_main_process:
        print(f"train={len(train_records)} val={len(val_records)} households, generated in {gen_seconds:.1f}s")

    train_ds = HouseholdTensorDataset(train_records, config)
    val_ds = HouseholdTensorDataset(val_records, config)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=collate)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate)

    model = ReliefFMNano(config)
    if accelerator.is_main_process:
        print(f"model parameters: {model.num_parameters():,}")
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    model, optimizer, train_loader, val_loader = accelerator.prepare(model, optimizer, train_loader, val_loader)

    log_path = out_dir / "run_log.jsonl"
    log_file = open(log_path, "a") if accelerator.is_main_process else None

    global_step = 0
    skipped_nonfinite = 0
    train_start = time.time()

    for epoch in range(args.epochs):
        model.train()
        for batch in train_loader:
            output = model(batch)
            losses = compute_loss(output, batch)
            loss = losses["total"]

            if not torch.isfinite(loss):
                skipped_nonfinite += 1
                optimizer.zero_grad()
                continue

            accelerator.backward(loss)
            accelerator.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            optimizer.zero_grad()
            global_step += 1

            if accelerator.is_main_process and global_step % args.log_every_steps == 0:
                record = {
                    "step": global_step, "epoch": epoch,
                    "total_loss": loss.item(),
                    "trajectory_loss": losses["trajectory_loss"].item(),
                    "distress_loss": losses["distress_loss"].item(),
                    "accounting_loss": losses["accounting_loss"].item(),
                    "elapsed_seconds": time.time() - train_start,
                }
                log_file.write(json.dumps(record) + "\n")
                log_file.flush()
                print(record)

            if global_step % args.eval_every_steps == 0:
                val_metrics = _evaluate(model, val_loader)
                if accelerator.is_main_process:
                    val_record = {"step": global_step, "epoch": epoch, "val": val_metrics}
                    log_file.write(json.dumps(val_record) + "\n")
                    log_file.flush()
                    print(val_record)
                model.train()

    final_val_metrics = _evaluate(model, val_loader)
    train_seconds = time.time() - train_start

    if accelerator.is_main_process:
        unwrapped = accelerator.unwrap_model(model)
        _save_checkpoint(
            unwrapped, optimizer, config, out_dir, args, manifest,
            final_val_metrics, gen_seconds, train_seconds, skipped_nonfinite, global_step,
        )
        print(f"done. step={global_step} skipped_nonfinite={skipped_nonfinite} final_val={final_val_metrics}")
        log_file.close()


@torch.no_grad()
def _evaluate(model, loader) -> dict:
    model.eval()
    totals = {"total": 0.0, "trajectory_loss": 0.0, "distress_loss": 0.0, "accounting_loss": 0.0}
    n = 0
    for batch in loader:
        output = model(batch)
        losses = compute_loss(output, batch)
        for k in totals:
            totals[k] += losses[k].item() if k != "total" else losses["total"].item()
        n += 1
    n = max(n, 1)
    return {k: v / n for k, v in totals.items()}


def _save_checkpoint(model, optimizer, config, out_dir, args, manifest, val_metrics, gen_seconds, train_seconds, skipped_nonfinite, step) -> None:
    ckpt_dir = out_dir / "checkpoint"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    state_dict = {k: v.contiguous() for k, v in model.state_dict().items()}
    save_file(state_dict, str(ckpt_dir / "model.safetensors"))

    torch.save(
        {"optimizer": optimizer.state_dict(), "step": step, "rng_state": torch.get_rng_state()},
        ckpt_dir / "training_state.pt",
    )

    meta = {
        "model_name": config.model_name,
        "model_version": "0.1.0",
        "contract_version": "1.0.0",
        "config": asdict(config),
        "training_args": vars(args),
        "data_manifest": manifest,
        "dataset_version": manifest.get("dataset_version", DATASET_VERSION),
        "calibration_version": CALIBRATION_VERSION,
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "num_parameters": model.num_parameters(),
        "generation_seconds": gen_seconds,
        "training_seconds": train_seconds,
        "training_steps": step,
        "skipped_nonfinite_steps": skipped_nonfinite,
        "final_val_metrics": val_metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    (ckpt_dir / "checkpoint_meta.json").write_text(json.dumps(meta, indent=2, default=str))


if __name__ == "__main__":
    main()
