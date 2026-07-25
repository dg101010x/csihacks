"""Runtime device helpers shared by Nano and Mini inference."""
from __future__ import annotations

import os

import torch


def resolve_device(requested: str | None = None) -> torch.device:
    """Resolve RELIEFFM_DEVICE without silently falling back from a bad choice."""
    value = (requested or os.environ.get("RELIEFFM_DEVICE", "auto")).lower()
    if value == "auto":
        value = "cuda" if torch.cuda.is_available() else "cpu"
    if value == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("RELIEFFM_DEVICE=cuda requested, but CUDA is unavailable")
    if value == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("RELIEFFM_DEVICE=mps requested, but MPS is unavailable")
    if value not in {"cpu", "cuda", "mps"}:
        raise ValueError("RELIEFFM_DEVICE must be one of: auto, cpu, cuda, mps")
    return torch.device(value)


def move_batch_to_device(
    batch: dict[str, torch.Tensor], device: torch.device
) -> dict[str, torch.Tensor]:
    return {key: value.to(device) for key, value in batch.items()}
