"""Section 19.1 — ReliefFM Nano target configuration, plus the sequence-length
and feature-count constants the tokenizer and model both need to agree on.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NanoConfig:
    model_name: str = "relieffm_nano"

    # Section 19.1 target configuration (verbatim).
    encoder_layers: int = 4
    decoder_layers: int = 2
    hidden_dimension: int = 256
    attention_heads: int = 8
    feedforward_dimension: int = 1024
    context_events: int = 256
    forecast_horizon_days: int = 30
    scenario_count: int = 32

    # Sequence padding budgets (not in the spec's config block — chosen to
    # comfortably cover ReliefSim's Nano-scale households, section 18).
    max_accounts: int = 5
    max_obligations: int = 8
    max_known_future_events: int = 24

    # Distress heads predict at these horizons (subset of section 26's
    # 7/14/30/60/90 that fits inside a 30-day forecast horizon).
    distress_horizons: tuple[int, ...] = (7, 14, 30)

    # Trajectory head quantile levels (section 25's daily distributions,
    # represented as a fixed quantile set rather than full densities).
    quantile_levels: tuple[float, ...] = (0.1, 0.5, 0.9)

    dropout: float = 0.1

    # Numeric feature widths — must match tokenize.py exactly.
    household_numeric_dim: int = 7
    account_numeric_dim: int = 4
    obligation_numeric_dim: int = 3
    event_numeric_dim: int = 9
    known_future_numeric_dim: int = 8


@dataclass
class MiniConfig:
    """Section 19.2 target configuration, adjusted to fit one session's GPU
    budget (context_events and horizon below spec's 1024/90, everything
    else close to spec). Gains section 21's horizon event-set decoder,
    section 22's global trajectory latent, and section 29-31's
    intervention-conditioned coupled sampling — none of which Nano has.
    Measured parameter count goes in the model card, not asserted here.
    """

    model_name: str = "relieffm_mini"

    # Total encoder_layers (8) split across three encoder modules, largest
    # share to the historical stream (section 3's actual research surface).
    context_encoder_layers: int = 2
    historical_encoder_layers: int = 4
    known_future_encoder_layers: int = 2
    decoder_layers: int = 4  # shared decoder stack, day queries + event-slot queries together

    hidden_dimension: int = 512
    attention_heads: int = 8
    feedforward_dimension: int = 2048  # SwiGLU inner dim
    context_events: int = 512
    forecast_horizon_days: int = 60
    scenario_count: int = 64
    max_event_slots: int = 96  # horizon event-set decoder query count (section 21)
    latent_dim: int = 32  # section 22's global trajectory latent z

    max_accounts: int = 5
    max_obligations: int = 10
    max_known_future_events: int = 48
    max_intervention_tokens: int = 1  # one proposed intervention per request (section 10)

    distress_horizons: tuple[int, ...] = (7, 14, 30, 60)
    quantile_levels: tuple[float, ...] = (0.1, 0.5, 0.9)
    dropout: float = 0.1

    # Numeric feature widths — must match ml/relieffm/mini/tokenize.py exactly.
    household_numeric_dim: int = 7
    account_numeric_dim: int = 4
    obligation_numeric_dim: int = 3
    event_numeric_dim: int = 9
    known_future_numeric_dim: int = 8
    intervention_numeric_dim: int = 6
    distress_engineered_dim: int = 10  # must match ml/baselines/gradient_boosted.py FEATURE_NAMES

    # Opt-in architecture upgrades (ml/relieffm/blocks.py's V2 blocks,
    # ml/relieffm/mini/historical_encoder.py's masked reconstruction head).
    # Defaults reproduce Mini's exact already-trained architecture --
    # changing these defaults would break `load_state_dict` on any
    # checkpoint trained before the change. Flash's preset
    # (ml/relieffm/presets.py) turns them on.
    use_qk_norm: bool = False
    n_kv_heads: int | None = None  # None = full multi-head attention (Mini's behavior)
    use_masked_pretraining: bool = False
    mask_ratio: float = 0.15
    use_activation_checkpointing: bool = False
