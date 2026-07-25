"""Wraps ReliefSim + the input compiler as a torch Dataset. Tokenization
happens once at construction (Nano-scale populations fit comfortably in
memory — see the data card for the actual household counts used)."""
from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset

from ml.datasets.compile import household_record_to_snapshot, household_record_to_targets
from ml.relieffm.config import NanoConfig
from ml.relieffm.tokenize import encode_snapshot, encode_targets
from ml.simulator.types import HouseholdRecord


class HouseholdTensorDataset(Dataset):
    def __init__(self, records: list[HouseholdRecord], config: NanoConfig):
        self.config = config
        self.examples: list[dict[str, np.ndarray]] = []
        for r in records:
            snapshot = household_record_to_snapshot(r)
            targets = household_record_to_targets(r)
            example = encode_snapshot(snapshot, config)
            example.update(encode_targets(targets, config))
            self.examples.append(example)

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, np.ndarray]:
        return self.examples[idx]


def collate(batch: list[dict[str, np.ndarray]]) -> dict[str, torch.Tensor]:
    out: dict[str, torch.Tensor] = {}
    for key in batch[0]:
        stacked = np.stack([b[key] for b in batch])
        tensor = torch.from_numpy(stacked)
        if tensor.dtype == torch.float64:
            tensor = tensor.float()
        out[key] = tensor
    return out
