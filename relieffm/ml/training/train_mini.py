"""ReliefFM Mini training: joint multi-task (trajectory, event-set,
distress, accounting, intervention-delta) in a single training loop rather
than the spec's sequential Stage Three/Four curriculum (section 64-65) —
a deliberate simplification for a one-session build, noted in the model
card. Every batch already carries an intervention example per household
(a zeroed, mask-excluded placeholder when the household has no eligible
obligation), so there's no separate intervention-only phase to schedule.

    python -m ml.training.train_mini --n_households 20000 --epochs 8 --out_dir runs/mini_v1
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import random
import shutil
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from accelerate import Accelerator
from safetensors.torch import save_file
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader

from ml.datasets.splits import assign_splits
from ml.datasets.writer import write_dataset, DATASET_VERSION
from ml.relieffm.mini.model import ReliefFMMini
from ml.relieffm.presets import PRESETS
from ml.simulator.population import generate_population
from ml.training.dataset_mini import EpochShuffleSampler, MiniTensorDataset, collate_mini
from ml.training.mini_losses import compute_mini_loss

CALIBRATION_VERSION = "calibration_uncalibrated_0.0.0"


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def _cosine_warmup(step: int, warmup_steps: int, total_steps: int) -> float:
    if step < warmup_steps:
        return step / max(warmup_steps, 1)
    progress = (step - warmup_steps) / max(total_steps - warmup_steps, 1)
    return 0.5 * (1.0 + math.cos(math.pi * min(progress, 1.0)))


def _read_resume_state(resume_from: str | None) -> dict:
    if not resume_from:
        return {}
    state_path = Path(resume_from) / "resume_state.json"
    if not state_path.is_file():
        raise FileNotFoundError(f"resume metadata not found: {state_path}")
    return json.loads(state_path.read_text())


def _save_recovery_checkpoint(
    accelerator: Accelerator,
    out_dir: Path,
    epoch: int,
    batch_in_epoch: int,
    global_step: int,
    skipped_nonfinite: int,
    as_of: datetime,
    best_val: float = float("inf"),
    best_step: int = 0,
) -> None:
    """Atomically replace the rolling full-state recovery checkpoint."""
    staging = out_dir / "recovery_staging"
    target = out_dir / "recovery"
    previous = out_dir / "recovery_previous"

    accelerator.wait_for_everyone()
    if accelerator.is_main_process:
        shutil.rmtree(staging, ignore_errors=True)
    accelerator.wait_for_everyone()
    accelerator.save_state(str(staging), safe_serialization=True)

    if accelerator.is_main_process:
        state = {
            "epoch": epoch,
            "batch_in_epoch": batch_in_epoch,
            "global_step": global_step,
            "skipped_nonfinite": skipped_nonfinite,
            "best_val": best_val,
            "best_step": best_step,
            "as_of": as_of.isoformat(),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        (staging / "resume_state.json").write_text(json.dumps(state, indent=2))
        shutil.rmtree(previous, ignore_errors=True)
        if target.exists():
            os.replace(target, previous)
        os.replace(staging, target)
        shutil.rmtree(previous, ignore_errors=True)
    accelerator.wait_for_everyone()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--preset", type=str, default="mini", choices=["mini", "flash"])
    p.add_argument("--n_households", type=int, default=20000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--history_days", type=int, default=120)
    p.add_argument("--horizon_days", type=int, default=None)  # defaults to MiniConfig's
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--batch_size", type=int, default=32)
    p.add_argument("--n_scenarios_train", type=int, default=4)
    p.add_argument("--n_scenarios_eval", type=int, default=8)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--weight_decay", type=float, default=0.01)
    p.add_argument("--warmup_frac", type=float, default=0.05)
    p.add_argument("--out_dir", type=str, default="runs/mini_v1")
    p.add_argument("--eval_every_steps", type=int, default=200)
    p.add_argument("--log_every_steps", type=int, default=20)
    p.add_argument("--gradient_accumulation_steps", type=int, default=1)
    p.add_argument("--recovery_every_steps", type=int, default=500)
    p.add_argument("--resume_from", type=str, default=None)
    p.add_argument("--activation_checkpointing", action="store_true")
    p.add_argument("--max_steps", type=int, default=None)
    p.add_argument(
        "--stop_after_steps",
        type=int,
        default=None,
        help=(
            "Stop cleanly after this many additional optimizer steps and leave "
            "a recovery checkpoint. Unlike --max_steps, this does not shorten "
            "the scheduler's full-run horizon."
        ),
    )
    p.add_argument(
        "--write_dataset",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.gradient_accumulation_steps < 1:
        raise ValueError("--gradient_accumulation_steps must be >= 1")
    if args.recovery_every_steps < 0:
        raise ValueError("--recovery_every_steps must be >= 0")
    if args.stop_after_steps is not None and args.stop_after_steps < 1:
        raise ValueError("--stop_after_steps must be >= 1")

    torch.set_float32_matmul_precision("high")
    accelerator = Accelerator(
        mixed_precision="bf16" if torch.cuda.is_available() else "no",
        gradient_accumulation_steps=args.gradient_accumulation_steps,
    )
    config = PRESETS[args.preset]()
    if args.horizon_days:
        config.forecast_horizon_days = args.horizon_days
    if args.activation_checkpointing:
        config.use_activation_checkpointing = True

    resume_state = _read_resume_state(args.resume_from)
    as_of = (
        datetime.fromisoformat(resume_state["as_of"])
        if resume_state
        else datetime.now(timezone.utc).replace(microsecond=0)
    )
    if accelerator.is_main_process:
        print(f"Generating {args.n_households} synthetic households (seed={args.seed})...")
    t0 = time.time()
    records = generate_population(
        args.n_households, seed=args.seed, as_of=as_of,
        history_days=args.history_days, horizon_days=config.forecast_horizon_days,
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

    t0 = time.time()
    train_ds = MiniTensorDataset(train_records, config, seed=args.seed)
    val_ds = MiniTensorDataset(val_records, config, seed=args.seed + 1)
    tokenize_seconds = time.time() - t0
    if accelerator.is_main_process:
        print(f"tokenized in {tokenize_seconds:.1f}s")

    train_sampler = EpochShuffleSampler(train_ds, seed=args.seed)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=train_sampler, collate_fn=collate_mini)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, collate_fn=collate_mini)

    model = ReliefFMMini(config)
    if accelerator.is_main_process:
        print(f"model parameters: {model.num_parameters():,}")
    optimizer = AdamW(
        model.parameters(),
        lr=args.lr,
        weight_decay=args.weight_decay,
        fused=torch.cuda.is_available(),
    )

    optimizer_steps_per_epoch = math.ceil(len(train_loader) / args.gradient_accumulation_steps)
    total_steps = max(optimizer_steps_per_epoch * args.epochs, 1)
    if args.max_steps:
        total_steps = min(total_steps, args.max_steps)
    warmup_steps = max(int(total_steps * args.warmup_frac), 1)
    scheduler = LambdaLR(optimizer, lr_lambda=lambda s: _cosine_warmup(s, warmup_steps, total_steps))

    model, optimizer, train_loader, val_loader, scheduler = accelerator.prepare(
        model, optimizer, train_loader, val_loader, scheduler
    )

    if args.resume_from:
        accelerator.load_state(args.resume_from)

    log_path = out_dir / "run_log.jsonl"
    log_file = open(log_path, "a") if accelerator.is_main_process else None

    global_step = int(resume_state.get("global_step", 0)) if resume_state else 0
    start_epoch = int(resume_state.get("epoch", 0)) if resume_state else 0
    start_batch = int(resume_state.get("batch_in_epoch", 0)) if resume_state else 0
    skipped_nonfinite = int(resume_state.get("skipped_nonfinite", 0)) if resume_state else 0
    best_val = float(resume_state.get("best_val", float("inf"))) if resume_state else float("inf")
    best_step = int(resume_state.get("best_step", 0)) if resume_state else 0
    stop_at_step = (
        global_step + args.stop_after_steps
        if args.stop_after_steps is not None
        else None
    )
    train_start = time.time()
    stopped_early = False
    for epoch in range(start_epoch, args.epochs):
        train_sampler.set_epoch(epoch)
        model.train()
        epoch_loader = train_loader
        if epoch == start_epoch and start_batch:
            epoch_loader = accelerator.skip_first_batches(train_loader, start_batch)

        reached_step_limit = False
        batch_in_epoch = start_batch if epoch == start_epoch else 0
        for batch_offset, batch in enumerate(epoch_loader, start=start_batch if epoch == start_epoch else 0):
            with accelerator.accumulate(model):
                output = model(batch, n_scenarios=args.n_scenarios_train, include_intervention=True)
                losses = compute_mini_loss(output, batch)
                loss = losses["total"]

                if not torch.isfinite(loss):
                    skipped_nonfinite += 1
                    optimizer.zero_grad(set_to_none=True)
                    _save_recovery_checkpoint(
                        accelerator, out_dir, epoch, batch_offset, global_step,
                        skipped_nonfinite, as_of, best_val, best_step,
                    )
                    raise FloatingPointError(
                        f"nonfinite loss at epoch={epoch} batch={batch_offset} step={global_step}"
                    )

                accelerator.backward(loss)
                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)

            if not accelerator.sync_gradients:
                continue

            global_step += 1
            batch_in_epoch = batch_offset + 1

            if accelerator.is_main_process and global_step % args.log_every_steps == 0:
                record = {
                    "step": global_step, "epoch": epoch, "lr": scheduler.get_last_lr()[0],
                    "total_loss": loss.item(),
                    "trajectory_loss": losses["trajectory_loss"].item(),
                    "event_set_loss": losses["event_set_loss"].item(),
                    "distress_loss": losses["distress_loss"].item(),
                    "accounting_loss": losses["accounting_loss"].item(),
                    "intervention_delta_loss": losses["intervention_delta_loss"].item(),
                    "masked_recon_loss": losses["masked_recon_loss"].item(),
                    "peak_gpu_memory_bytes": (
                        torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
                    ),
                    "elapsed_seconds": time.time() - train_start,
                }
                log_file.write(json.dumps(record) + "\n")
                log_file.flush()
                print(record)

            if global_step % args.eval_every_steps == 0:
                val_metrics = _evaluate(model, val_loader, args.n_scenarios_eval)
                if val_metrics["total"] < best_val:
                    best_val = val_metrics["total"]
                    best_step = global_step
                    _save_best_weights(accelerator, model, out_dir)
                if accelerator.is_main_process:
                    val_record = {"step": global_step, "epoch": epoch, "val": val_metrics}
                    log_file.write(json.dumps(val_record) + "\n")
                    log_file.flush()
                    print(val_record)
                model.train()

            if args.recovery_every_steps and global_step % args.recovery_every_steps == 0:
                _save_recovery_checkpoint(
                    accelerator, out_dir, epoch, batch_in_epoch, global_step,
                    skipped_nonfinite, as_of, best_val, best_step,
                )

            if (
                (args.max_steps and global_step >= args.max_steps)
                or (stop_at_step is not None and global_step >= stop_at_step)
            ):
                reached_step_limit = True
                break

        start_batch = 0
        if reached_step_limit:
            epoch_finished = batch_in_epoch >= len(train_loader)
            _save_recovery_checkpoint(
                accelerator,
                out_dir,
                epoch + 1 if epoch_finished else epoch,
                0 if epoch_finished else batch_in_epoch,
                global_step,
                skipped_nonfinite,
                as_of,
                best_val,
                best_step,
            )
        elif not args.recovery_every_steps or global_step % args.recovery_every_steps:
            _save_recovery_checkpoint(
                accelerator, out_dir, epoch + 1, 0, global_step,
                skipped_nonfinite, as_of, best_val, best_step,
            )
        if reached_step_limit:
            stopped_early = global_step < total_steps
            break

    if stopped_early:
        if accelerator.is_main_process:
            print(
                f"chunk complete. step={global_step}/{total_steps}; "
                f"resume from {out_dir / 'recovery'}"
            )
            log_file.close()
        accelerator.end_training()
        return

    final_val_metrics = _evaluate(model, val_loader, args.n_scenarios_eval)
    if best_step == 0 or final_val_metrics["total"] < best_val:
        best_val = final_val_metrics["total"]
        best_step = global_step
        _save_best_weights(accelerator, model, out_dir)
    train_seconds = time.time() - train_start

    if accelerator.is_main_process:
        unwrapped = accelerator.unwrap_model(model)
        _save_checkpoint(
            unwrapped, optimizer, scheduler, config, out_dir, args, manifest,
            final_val_metrics, gen_seconds, tokenize_seconds, train_seconds, skipped_nonfinite, global_step,
        )
        best_meta = json.loads((out_dir / "checkpoint" / "checkpoint_meta.json").read_text())
        best_meta["training_steps"] = best_step
        best_meta["last_training_step"] = global_step
        best_meta["checkpoint_selection"] = "lowest validation total loss"
        best_meta["selected_validation_total"] = best_val
        best_meta["last_model_val_metrics"] = best_meta.pop("final_val_metrics")
        (out_dir / "checkpoint_best" / "checkpoint_meta.json").write_text(
            json.dumps(best_meta, indent=2, default=str)
        )
        print(f"done. step={global_step} skipped_nonfinite={skipped_nonfinite} final_val={final_val_metrics}")
        log_file.close()


@torch.no_grad()
def _evaluate(model, loader, n_scenarios: int) -> dict:
    model.eval()
    totals = {"total": 0.0, "trajectory_loss": 0.0, "event_set_loss": 0.0, "distress_loss": 0.0, "accounting_loss": 0.0, "intervention_delta_loss": 0.0}
    n = 0
    for batch in loader:
        output = model(batch, n_scenarios=n_scenarios, include_intervention=True)
        losses = compute_mini_loss(output, batch)
        for k in totals:
            totals[k] += losses[k].item()
        n += 1
    n = max(n, 1)
    return {k: v / n for k, v in totals.items()}


def _save_best_weights(accelerator: Accelerator, model, out_dir: Path) -> None:
    state_dict = accelerator.get_state_dict(model)
    if accelerator.is_main_process:
        best_dir = out_dir / "checkpoint_best"
        best_dir.mkdir(parents=True, exist_ok=True)
        cpu_state = {
            key: value.detach().cpu().contiguous()
            for key, value in state_dict.items()
        }
        save_file(cpu_state, str(best_dir / "model.safetensors"))
    accelerator.wait_for_everyone()


def _save_checkpoint(model, optimizer, scheduler, config, out_dir, args, manifest, val_metrics, gen_seconds, tokenize_seconds, train_seconds, skipped_nonfinite, step) -> None:
    ckpt_dir = out_dir / "checkpoint"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    state_dict = {
        key: value.detach().cpu().contiguous()
        for key, value in model.state_dict().items()
    }
    save_file(state_dict, str(ckpt_dir / "model.safetensors"))

    training_state = {
        "optimizer": optimizer.state_dict(),
        "scheduler": scheduler.state_dict(),
        "step": step,
        "torch_rng_state": torch.get_rng_state(),
        "numpy_rng_state": np.random.get_state(),
        "python_rng_state": random.getstate(),
    }
    if torch.cuda.is_available():
        training_state["cuda_rng_state_all"] = torch.cuda.get_rng_state_all()
    torch.save(training_state, ckpt_dir / "training_state.pt")

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
        "tokenize_seconds": tokenize_seconds,
        "training_seconds": train_seconds,
        "training_steps": step,
        "skipped_nonfinite_steps": skipped_nonfinite,
        "final_val_metrics": val_metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    (ckpt_dir / "checkpoint_meta.json").write_text(json.dumps(meta, indent=2, default=str))


if __name__ == "__main__":
    main()
