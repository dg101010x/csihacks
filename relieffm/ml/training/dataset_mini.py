"""Mini's tensor dataset: tokenizes snapshot + trajectory targets + event-set
targets + one intervention example per household, all at construction time
(same in-memory approach as Nano's `ml/training/dataset.py`).
"""
from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset, Sampler

from ml.datasets.compile import (
    household_record_to_event_set_targets,
    household_record_to_intervention_example,
    household_record_to_snapshot,
    household_record_to_targets,
)
from ml.relieffm.config import MiniConfig
from ml.relieffm.mini.tokenize import (
    encode_event_set_targets,
    encode_intervention_example,
    encode_mini_snapshot,
    encode_mini_targets,
)
from ml.simulator.types import HouseholdRecord
from ml.training.dataset import collate


class MiniTensorDataset(Dataset):
    def __init__(self, records: list[HouseholdRecord], config: MiniConfig, seed: int = 0):
        self.config = config
        rng = np.random.default_rng(seed)
        self.examples: list[dict[str, np.ndarray]] = []
        for r in records:
            snapshot = household_record_to_snapshot(r)
            targets = household_record_to_targets(r)
            event_targets = household_record_to_event_set_targets(r, config)
            intervention_example = household_record_to_intervention_example(r, config, rng)

            example = encode_mini_snapshot(snapshot, config)
            example.update(encode_mini_targets(targets, config))
            example.update(encode_event_set_targets(event_targets, config))
            example.update(encode_intervention_example(intervention_example, snapshot, config))
            self.examples.append(example)

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, np.ndarray]:
        return self.examples[idx]


class EpochShuffleSampler(Sampler[int]):
    """Deterministic per-epoch shuffle, independent of ambient RNG state.

    This makes a recovery checkpoint's ``epoch`` and ``batch_in_epoch``
    sufficient to reproduce the remaining sample order.
    """

    def __init__(self, data_source: Dataset, seed: int):
        self.data_source = data_source
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __iter__(self):
        generator = torch.Generator()
        generator.manual_seed(self.seed + self.epoch)
        return iter(torch.randperm(len(self.data_source), generator=generator).tolist())

    def __len__(self) -> int:
        return len(self.data_source)


def collate_mini(batch: list[dict[str, np.ndarray]]) -> dict[str, torch.Tensor]:
    """Stack a batch and remove padding beyond its longest sequence.

    Historical events are right-aligned to preserve the most recent events;
    known-future events are left-aligned in chronological order.
    """
    out = collate(batch)

    event_length = max(int(out["event_mask"].sum(dim=1).max().item()), 1)
    for key in ("event_cat", "event_numeric", "event_mask"):
        out[key] = out[key][:, -event_length:]

    known_length = max(int(out["known_mask"].sum(dim=1).max().item()), 1)
    for key in ("known_cat", "known_numeric", "known_mask"):
        out[key] = out[key][:, :known_length]

    return out
