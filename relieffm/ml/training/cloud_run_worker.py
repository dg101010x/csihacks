"""One bounded ReliefFM Flash task for an RTX Cloud Run job.

Cloud Run GPU tasks are limited to one hour. A multi-task job runs these
workers sequentially; each task downloads the latest full-state recovery
checkpoint, advances the original training schedule by a bounded number of
optimizer steps, and uploads the next recovery checkpoint. Once training is
complete, later tasks observe the completion marker and exit immediately.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from google.cloud import storage


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def _download_prefix(bucket, prefix: str, destination: Path) -> int:
    count = 0
    for blob in bucket.list_blobs(prefix=prefix):
        if blob.name.endswith("/"):
            continue
        relative = Path(blob.name).relative_to(prefix)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(target)
        count += 1
    return count


def _upload_tree(bucket, source: Path, prefix: str) -> int:
    if not source.exists():
        return 0
    count = 0
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        bucket.blob(f"{prefix}/{relative}").upload_from_filename(path)
        count += 1
    return count


def _run(command: list[str]) -> None:
    print("running:", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def _preflight(bucket, run_prefix: str, work_dir: Path) -> None:
    report_path = work_dir / "preflight.json"
    command = [
        "python",
        "-m",
        "ml.training.benchmark_mini",
        "--preset",
        "flash",
        "--batch_size",
        os.environ.get("BATCH_SIZE", "16"),
        "--n_scenarios",
        os.environ.get("N_SCENARIOS_TRAIN", "4"),
        "--steps",
        os.environ.get("PREFLIGHT_STEPS", "3"),
        "--activation_checkpointing",
        "--out_path",
        str(report_path),
    ]
    _run(command)
    bucket.blob(f"{run_prefix}/preflight.json").upload_from_filename(report_path)
    print(f"uploaded gs://{bucket.name}/{run_prefix}/preflight.json", flush=True)


def _train_chunk(bucket, run_prefix: str, work_dir: Path) -> None:
    completed_blob = bucket.blob(f"{run_prefix}/COMPLETED.json")
    if completed_blob.exists():
        print("training is already complete; this task has nothing to do", flush=True)
        return

    run_dir = work_dir / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    downloaded = _download_prefix(bucket, f"{run_prefix}/state/", run_dir)
    print(f"downloaded {downloaded} persisted state files", flush=True)

    command = [
        "python",
        "-m",
        "ml.training.train_mini",
        "--preset",
        "flash",
        "--n_households",
        os.environ.get("N_HOUSEHOLDS", "25000"),
        "--epochs",
        os.environ.get("EPOCHS", "12"),
        "--batch_size",
        os.environ.get("BATCH_SIZE", "16"),
        "--n_scenarios_train",
        os.environ.get("N_SCENARIOS_TRAIN", "4"),
        "--n_scenarios_eval",
        os.environ.get("N_SCENARIOS_EVAL", "8"),
        "--gradient_accumulation_steps",
        os.environ.get("GRADIENT_ACCUMULATION_STEPS", "2"),
        "--recovery_every_steps",
        os.environ.get("RECOVERY_EVERY_STEPS", "50"),
        "--lr",
        os.environ.get("LEARNING_RATE", "2e-4"),
        "--eval_every_steps",
        os.environ.get("EVAL_EVERY_STEPS", "600"),
        "--seed",
        os.environ.get("TRAIN_SEED", "1"),
        "--stop_after_steps",
        _required_env("CHUNK_STEPS"),
        "--activation_checkpointing",
        "--no-write_dataset",
        "--out_dir",
        str(run_dir),
    ]
    recovery = run_dir / "recovery"
    if (recovery / "resume_state.json").is_file():
        command.extend(["--resume_from", str(recovery)])

    try:
        _run(command)
    finally:
        uploaded = _upload_tree(bucket, run_dir / "recovery", f"{run_prefix}/state/recovery")
        uploaded += _upload_tree(
            bucket, run_dir / "checkpoint_best", f"{run_prefix}/state/checkpoint_best"
        )
        log_path = run_dir / "run_log.jsonl"
        if log_path.is_file():
            bucket.blob(f"{run_prefix}/state/run_log.jsonl").upload_from_filename(log_path)
            uploaded += 1
        print(f"uploaded {uploaded} recovery/state files", flush=True)

    if not (run_dir / "checkpoint" / "checkpoint_meta.json").is_file():
        state = json.loads((recovery / "resume_state.json").read_text())
        print(f"chunk complete at optimizer step {state['global_step']}", flush=True)
        return

    eval_path = run_dir / "eval_report.json"
    _run(
        [
            "python",
            "-m",
            "ml.evaluation.run_eval_mini",
            "--checkpoint_dir",
            str(run_dir / "checkpoint_best"),
            "--n_households",
            "1500",
            "--n_scenarios",
            "16",
            "--seed",
            os.environ.get("EVAL_SEED", "99991"),
            "--out_path",
            str(eval_path),
        ]
    )
    uploaded = _upload_tree(bucket, run_dir, f"{run_prefix}/final")
    completion = {
        "run_id": _required_env("RUN_ID"),
        "training_steps": json.loads(
            (run_dir / "checkpoint" / "checkpoint_meta.json").read_text()
        )["training_steps"],
        "cloud_run_execution": os.environ.get("CLOUD_RUN_EXECUTION"),
        "cloud_run_task_index": os.environ.get("CLOUD_RUN_TASK_INDEX"),
    }
    completed_blob.upload_from_string(
        json.dumps(completion, indent=2), content_type="application/json"
    )
    print(f"training and evaluation complete; uploaded {uploaded} final files", flush=True)


def main() -> None:
    bucket_name = _required_env("BUCKET")
    run_id = _required_env("RUN_ID")
    mode = os.environ.get("MODE", "preflight")
    bucket = storage.Client().bucket(bucket_name)
    run_prefix = f"runs/{run_id}"
    work_dir = Path("/tmp/relieffm")
    work_dir.mkdir(parents=True, exist_ok=True)

    if mode == "preflight":
        _preflight(bucket, run_prefix, work_dir)
    elif mode == "train":
        _train_chunk(bucket, run_prefix, work_dir)
    else:
        raise ValueError(f"unsupported MODE={mode!r}")


if __name__ == "__main__":
    main()
