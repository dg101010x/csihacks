"""Section 61 exit condition: one household can move from
HouseholdSnapshotV1 to model tensors and back into a valid
ForecastResponseV1. Uses a freshly-initialized (untrained) model on disk —
this proves the pipeline round-trips correctly, not that predictions are
good (that's what ml/evaluation/run_eval.py measures against a trained
checkpoint).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta

import pytest
import torch
from safetensors.torch import save_file

from ml.relieffm.config import NanoConfig
from ml.relieffm.model import ReliefFMNano
from relief_contracts.fixtures import minimal_forecast_request, minimal_intervention_request
from relief_contracts.schemas import ForecastResponseV1, Intervention
from services.model_inference import inference
from services.model_inference.intervention import InterventionError, apply_intervention


def _write_fake_checkpoint(tmp_path, config: NanoConfig):
    ckpt_dir = tmp_path / "checkpoint"
    ckpt_dir.mkdir()
    model = ReliefFMNano(config)
    save_file(model.state_dict(), str(ckpt_dir / "model.safetensors"))
    meta = {
        "model_name": "relieffm_nano",
        "model_version": "0.0.0-stagezero",
        "dataset_version": "relief_data_test",
        "calibration_version": "calibration_uncalibrated_0.0.0",
        "config": asdict(config),
    }
    (ckpt_dir / "checkpoint_meta.json").write_text(json.dumps(meta))
    return ckpt_dir


def test_snapshot_to_tensors_to_forecast_response(tmp_path):
    config = NanoConfig()
    ckpt_dir = _write_fake_checkpoint(tmp_path, config)
    loaded = inference.LoadedModel(str(ckpt_dir))

    request = minimal_forecast_request()
    response = inference.run_forecast(
        loaded,
        snapshot=request.snapshot,
        horizon_days=request.horizon_days,
        scenario_count=request.scenario_count,
        request_id=request.request_id,
        forecast_id="forecast_test_01",
    )

    assert isinstance(response, ForecastResponseV1)
    assert len(response.daily_summary) == request.horizon_days
    assert len(response.trajectories) == min(request.scenario_count, config.scenario_count)
    # round-trips through the wire format (JSON) without loss
    restored = ForecastResponseV1.model_validate_json(response.model_dump_json())
    assert restored == response


def test_intervention_round_trip(tmp_path):
    config = NanoConfig()
    ckpt_dir = _write_fake_checkpoint(tmp_path, config)
    loaded = inference.LoadedModel(str(ckpt_dir))

    request = minimal_intervention_request()
    modified_snapshot, added_cost = apply_intervention(request.snapshot, request.intervention)
    assert modified_snapshot.household_id == request.snapshot.household_id

    response = inference.run_forecast(
        loaded,
        snapshot=modified_snapshot,
        horizon_days=request.horizon_days,
        scenario_count=request.scenario_count,
        request_id=request.request_id,
        forecast_id="intervention_test_01",
    )
    assert len(response.daily_summary) == request.horizon_days


def test_known_future_events_never_altered_by_split_payment():
    request = minimal_intervention_request()
    original_total = sum(e.amount_cents for e in request.snapshot.known_future_events)
    modified_snapshot, _ = apply_intervention(request.snapshot, request.intervention)
    # split_payment must preserve total scheduled amount for that obligation
    # (redistributes timing/amount split, doesn't create or destroy money)
    target_obl = request.intervention.obligation_id
    original_obl_total = sum(
        e.amount_cents for e in request.snapshot.known_future_events if e.obligation_id == target_obl
    )
    modified_obl_total = sum(
        e.amount_cents for e in modified_snapshot.known_future_events if e.obligation_id == target_obl
    )
    assert original_obl_total == modified_obl_total
    second = next(
        event
        for event in modified_snapshot.known_future_events
        if event.event_id.endswith("_split_b")
    )
    assert second.effective_time == datetime.fromisoformat(
        request.intervention.parameters["second_payment_date"]
    )


def test_split_payment_rejects_amounts_that_change_the_total():
    request = minimal_intervention_request()
    invalid = request.intervention.model_copy(
        update={
            "parameters": {
                "first_payment_cents": 1,
                "second_payment_cents": 1,
            }
        }
    )

    with pytest.raises(InterventionError, match="preserve the original total"):
        apply_intervention(request.snapshot, invalid)


@pytest.mark.parametrize(
    ("action_type", "parameters", "expected_amount_cents", "expected_cost_cents"),
    [
        ("waive_fee", {"waive_amount_cents": 10_000}, 170_000, 0),
        ("hardship_program", {"reduction_fraction": 0.25}, 135_000, 0),
        ("reduce_payment", {"reduction_fraction": 0.1}, 162_000, 0),
        (
            "refinance",
            {"reduction_fraction": 0.2, "added_cost_cents": 1_234},
            144_000,
            1_234,
        ),
    ],
)
def test_amount_changing_interventions_apply_request_parameters(
    action_type, parameters, expected_amount_cents, expected_cost_cents
):
    request = minimal_intervention_request()
    intervention = Intervention(
        action_type=action_type,
        obligation_id=request.intervention.obligation_id,
        parameters=parameters,
    )

    modified, added_cost = apply_intervention(request.snapshot, intervention)

    target_events = [
        event
        for event in modified.known_future_events
        if event.obligation_id == intervention.obligation_id
    ]
    assert target_events[0].amount_cents == expected_amount_cents
    assert added_cost == expected_cost_cents


def test_delay_payment_uses_requested_days_and_cost():
    request = minimal_intervention_request()
    original = next(
        event
        for event in request.snapshot.known_future_events
        if event.obligation_id == request.intervention.obligation_id
    )
    intervention = Intervention(
        action_type="delay_payment",
        obligation_id=request.intervention.obligation_id,
        parameters={"delay_days": 5, "added_cost_cents": 321},
    )

    modified, added_cost = apply_intervention(request.snapshot, intervention)

    delayed = next(
        event
        for event in modified.known_future_events
        if event.obligation_id == intervention.obligation_id
    )
    assert delayed.effective_time == original.effective_time + timedelta(days=5)
    assert added_cost == 321


def test_pause_subscription_uses_requested_duration():
    request = minimal_intervention_request()
    intervention = Intervention(
        action_type="pause_subscription",
        obligation_id=request.intervention.obligation_id,
        parameters={"duration_days": 7},
    )

    modified, _ = apply_intervention(request.snapshot, intervention)

    assert not any(
        event.obligation_id == intervention.obligation_id
        and event.effective_time <= request.snapshot.as_of + timedelta(days=7)
        for event in modified.known_future_events
    )


def test_reduction_fraction_is_bounded():
    request = minimal_intervention_request()
    intervention = Intervention(
        action_type="reduce_payment",
        obligation_id=request.intervention.obligation_id,
        parameters={"reduction_fraction": 1.1},
    )

    with pytest.raises(InterventionError, match="between 0 and 1"):
        apply_intervention(request.snapshot, intervention)
