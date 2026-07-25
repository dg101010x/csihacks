"""Named `MiniConfig` presets. Flash uses the same top-level ReliefFM
composition as Mini, with opt-in V2 blocks and pretraining heads. Its
deeper, 64-dimension-per-head layout stays separate from Mini's frozen
default configuration.
"""
from __future__ import annotations

from .config import MiniConfig


def mini_config(**overrides) -> MiniConfig:
    cfg = MiniConfig()
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


def flash_config(**overrides) -> MiniConfig:
    cfg = MiniConfig(
        model_name="relieffm_flash",
        hidden_dimension=1280,
        attention_heads=20,
        feedforward_dimension=3584,
        context_encoder_layers=4,
        historical_encoder_layers=11,
        known_future_encoder_layers=4,
        decoder_layers=11,
        context_events=1024,
        max_event_slots=128,
        max_known_future_events=64,
        latent_dim=64,
        forecast_horizon_days=60,
        scenario_count=64,
        max_accounts=5,
        max_obligations=10,
        # A 4:1 query-to-KV ratio keeps every attention head at 64
        # dimensions while reducing KV projection and attention cost.
        use_qk_norm=True,
        n_kv_heads=5,
        use_masked_pretraining=True,
        mask_ratio=0.15,
    )
    for k, v in overrides.items():
        setattr(cfg, k, v)
    return cfg


PRESETS = {"mini": mini_config, "flash": flash_config}
