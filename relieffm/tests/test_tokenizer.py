from datetime import datetime

import numpy as np

from ml.datasets.compile import household_record_to_snapshot, household_record_to_targets
from ml.relieffm.config import NanoConfig
from ml.relieffm.tokenize import encode_snapshot, encode_targets
from ml.simulator.population import generate_household

AS_OF = datetime(2026, 7, 25, 12, 0, 0)


def test_encoded_shapes_match_config():
    cfg = NanoConfig()
    r = generate_household("hh_tok", seed=2, as_of=AS_OF)
    snapshot = household_record_to_snapshot(r)
    enc = encode_snapshot(snapshot, cfg)

    assert enc["household_numeric"].shape == (cfg.household_numeric_dim,)
    assert enc["account_cat"].shape == (cfg.max_accounts, 1)
    assert enc["account_numeric"].shape == (cfg.max_accounts, cfg.account_numeric_dim)
    assert enc["obligation_cat"].shape == (cfg.max_obligations, 4)
    assert enc["event_cat"].shape == (cfg.context_events, 7)
    assert enc["event_numeric"].shape == (cfg.context_events, cfg.event_numeric_dim)
    assert enc["known_cat"].shape == (cfg.max_known_future_events, 4)

    # masks must be exactly 0/1 and never exceed the real token count
    assert set(np.unique(enc["event_mask"]).tolist()) <= {0.0, 1.0}
    assert enc["event_mask"].sum() == len(snapshot.historical_events[-cfg.context_events:])
    assert enc["account_mask"].sum() == min(len(snapshot.accounts), cfg.max_accounts)


def test_target_shapes_match_horizon():
    cfg = NanoConfig()
    r = generate_household("hh_tok2", seed=6, as_of=AS_OF)
    targets = household_record_to_targets(r)
    enc = encode_targets(targets, cfg)
    assert enc["target_full_balance_cents"].shape == (cfg.forecast_horizon_days,)
    assert enc["target_distress"].shape == (len(cfg.distress_horizons), 3)
