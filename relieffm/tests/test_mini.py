"""Mini-specific tests: catches the intervention-delta indexing bug found
during evaluation (delta arrays were being read from the historical window
instead of the forecast horizon, producing all-zero targets), plus basic
shape/gradient sanity for the new architecture.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import numpy.random as npr
import torch

from ml.datasets.compile import (
    household_record_to_event_set_targets,
    household_record_to_intervention_example,
    household_record_to_snapshot,
    household_record_to_targets,
)
from ml.relieffm.config import MiniConfig
from ml.relieffm.mini.model import ReliefFMMini
from ml.relieffm.mini.tokenize import encode_event_set_targets, encode_intervention_example, encode_mini_snapshot, encode_mini_targets
from ml.relieffm.presets import flash_config, mini_config
from ml.simulator.population import generate_household, generate_population
from ml.training.dataset import collate
from ml.training.dataset_mini import collate_mini
from ml.training.mini_losses import compute_mini_loss

AS_OF = datetime(2026, 7, 25, 12, 0, 0)


def _build_batch(n_households: int, seed: int, config: MiniConfig):
    records = generate_population(n_households, seed=seed, as_of=AS_OF, history_days=120, horizon_days=config.forecast_horizon_days)
    rng = npr.default_rng(seed)
    encs = []
    for r in records:
        snap = household_record_to_snapshot(r)
        tgt = household_record_to_targets(r)
        ev_tgt = household_record_to_event_set_targets(r, config)
        iv_example = household_record_to_intervention_example(r, config, rng)
        e = encode_mini_snapshot(snap, config)
        e.update(encode_mini_targets(tgt, config))
        e.update(encode_event_set_targets(ev_tgt, config))
        e.update(encode_intervention_example(iv_example, snap, config))
        encs.append(e)
    return collate(encs), records


def test_intervention_deltas_are_not_all_zero():
    """Regression test for the history/horizon offset bug: at least some
    households with a real intervention must show nonzero balance deltas
    somewhere in the forecast horizon."""
    config = MiniConfig(forecast_horizon_days=30)
    rng = npr.default_rng(1)
    any_nonzero = False
    for seed in range(20):
        r = generate_household(f"hh_delta_{seed}", seed=seed, as_of=AS_OF, history_days=90, horizon_days=config.forecast_horizon_days)
        ex = household_record_to_intervention_example(r, config, rng)
        if ex.has_intervention and any(d != 0 for d in ex.delta_daily_balance_cents):
            any_nonzero = True
            break
    assert any_nonzero, "no household produced a nonzero intervention delta -- likely an indexing regression"


def test_event_set_targets_within_slot_budget():
    config = MiniConfig(forecast_horizon_days=30)
    r = generate_household("hh_evset", seed=5, as_of=AS_OF, history_days=90, horizon_days=config.forecast_horizon_days)
    targets = household_record_to_event_set_targets(r, config)
    assert 0 <= targets.n_true_events <= config.max_event_slots
    assert sum(targets.valid_mask) == targets.n_true_events


def test_mini_model_forward_backward_small():
    config = MiniConfig(
        hidden_dimension=32, attention_heads=4, feedforward_dimension=64,
        context_events=32, max_known_future_events=8, max_event_slots=16,
        forecast_horizon_days=14, max_accounts=5, max_obligations=6,
        context_encoder_layers=1, historical_encoder_layers=1, known_future_encoder_layers=1, decoder_layers=1,
        latent_dim=8,
    )
    batch, _ = _build_batch(4, seed=42, config=config)
    model = ReliefFMMini(config)
    out = model(batch, n_scenarios=2, include_intervention=True)
    losses = compute_mini_loss(out, batch)
    assert torch.isfinite(losses["total"])
    losses["total"].backward()
    grad_params = [n for n, p in model.named_parameters() if p.grad is not None]
    no_grad_params = [n for n, p in model.named_parameters() if p.grad is None]
    # only the diagnostic reason-factor head is expected to have no grad
    assert all("reason_factor_head" in n for n in no_grad_params), no_grad_params
    assert len(grad_params) > 0


def test_flash_reconstructs_every_masked_event_field_with_gradients():
    config = MiniConfig(
        hidden_dimension=32, attention_heads=4, feedforward_dimension=64,
        context_events=32, max_known_future_events=8, max_event_slots=16,
        forecast_horizon_days=14, max_accounts=5, max_obligations=6,
        context_encoder_layers=1, historical_encoder_layers=1,
        known_future_encoder_layers=1, decoder_layers=1, latent_dim=8,
        use_qk_norm=True, n_kv_heads=2, use_masked_pretraining=True,
        mask_ratio=1.0, use_activation_checkpointing=True,
    )
    batch, _ = _build_batch(3, seed=52, config=config)
    model = ReliefFMMini(config)
    model.train()
    out = model(batch, n_scenarios=2, include_intervention=True)
    assert out.masked_reconstruction is not None
    assert len(out.masked_reconstruction["categorical_logits"]) == batch["event_cat"].shape[-1]
    assert out.masked_reconstruction["numeric_prediction"].shape[-1] == batch["event_numeric"].shape[-1]

    losses = compute_mini_loss(out, batch)
    assert torch.isfinite(losses["total"])
    losses["total"].backward()
    for head in model.historical_encoder.masked_categorical_heads:
        assert head.weight.grad is not None
    assert model.historical_encoder.masked_numeric_head.weight.grad is not None


def test_collate_mini_trims_only_padding_and_preserves_alignment():
    def example(event_count: int, known_count: int):
        event_mask = np.zeros(6, dtype=np.float32)
        event_mask[-event_count:] = 1
        event_cat = np.zeros((6, 2), dtype=np.int64)
        event_cat[-event_count:, 0] = np.arange(1, event_count + 1)
        known_mask = np.zeros(5, dtype=np.float32)
        known_mask[:known_count] = 1
        known_cat = np.zeros((5, 2), dtype=np.int64)
        known_cat[:known_count, 0] = np.arange(1, known_count + 1)
        return {
            "event_mask": event_mask,
            "event_cat": event_cat,
            "event_numeric": np.zeros((6, 3), dtype=np.float32),
            "known_mask": known_mask,
            "known_cat": known_cat,
            "known_numeric": np.zeros((5, 3), dtype=np.float32),
        }

    raw = [example(2, 1), example(4, 3)]
    full = collate(raw)
    trimmed = collate_mini(raw)
    assert trimmed["event_mask"].shape[1] == 4
    assert trimmed["known_mask"].shape[1] == 3
    assert torch.equal(trimmed["event_cat"], full["event_cat"][:, -4:])
    assert torch.equal(trimmed["known_cat"], full["known_cat"][:, :3])


def test_preset_parameter_budgets_and_frozen_mini_signature():
    with torch.device("meta"):
        mini = ReliefFMMini(mini_config())
        flash = ReliefFMMini(flash_config())
    assert mini.num_parameters() == 59_641_666
    assert 590_000_000 <= flash.num_parameters() <= 610_000_000
