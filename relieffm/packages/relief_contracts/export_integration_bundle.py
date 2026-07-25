"""Build the versioned handoff bundle consumed by the Plan Two gateway."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import torch

from ml.datasets.compile import household_record_to_snapshot
from ml.simulator.population import generate_household
from relief_contracts.export_json_schema import MODELS
from relief_contracts.fixtures import (
    minimal_forecast_request,
    minimal_intervention_request,
)
from relief_contracts.schemas import (
    ForecastRequestV1,
    Intervention,
    InterventionSimulationRequestV1,
)
from services.model_inference.app import app
from services.model_inference.inference_mini import (
    LoadedMiniModel,
    run_forecast_mini,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _realistic_requests(
    horizon_days: int, scenario_count: int
) -> tuple[ForecastRequestV1, InterventionSimulationRequestV1]:
    record = generate_household(
        "integration_hh_20260725",
        seed=20260725,
        as_of=datetime(2026, 7, 25, 12, tzinfo=timezone.utc),
        history_days=120,
        horizon_days=horizon_days,
    )
    snapshot = household_record_to_snapshot(record)
    target_event = next(
        event for event in snapshot.known_future_events if event.obligation_id is not None
    )
    first_payment_cents = target_event.amount_cents // 2
    intervention = Intervention(
        action_type="split_payment",
        obligation_id=target_event.obligation_id,
        parameters={
            "first_payment_cents": first_payment_cents,
            "second_payment_cents": target_event.amount_cents - first_payment_cents,
            "second_payment_date": (
                target_event.effective_time + timedelta(days=14)
            ).isoformat(),
        },
    )
    return (
        ForecastRequestV1(
            contract_version="1.0.0",
            request_id="forecast_req_mini_20260725_122238",
            snapshot=snapshot,
            horizon_days=horizon_days,
            scenario_count=scenario_count,
            requested_outputs=[
                "daily_balance_trajectories",
                "distress_probabilities",
                "income_distribution",
                "variable_spending_distribution",
            ],
        ),
        InterventionSimulationRequestV1(
            contract_version="1.0.0",
            request_id="intervention_req_mini_20260725_122238",
            snapshot=snapshot,
            base_forecast_id="forecast_fixture_mini_20260725_122238",
            intervention=intervention,
            horizon_days=horizon_days,
            scenario_count=scenario_count,
        ),
    )


def build_bundle(out_dir: Path, checkpoint_dir: Path | None = None) -> None:
    schemas_dir = out_dir / "schemas"
    fixtures_dir = out_dir / "fixtures"

    for model in MODELS:
        _write_json(schemas_dir / f"{model.__name__}.schema.json", model.model_json_schema())

    forecast_request = minimal_forecast_request()
    intervention_request = minimal_intervention_request()
    _write_json(
        fixtures_dir / "forecast_request.json",
        forecast_request.model_dump(mode="json"),
    )
    _write_json(
        fixtures_dir / "intervention_request.json",
        intervention_request.model_dump(mode="json"),
    )
    _write_json(out_dir / "openapi.json", app.openapi())

    if checkpoint_dir is not None:
        loaded = LoadedMiniModel(str(checkpoint_dir), device="cpu")
        horizon_days = loaded.config.forecast_horizon_days
        scenario_count = min(8, loaded.config.scenario_count)
        forecast_request, intervention_request = _realistic_requests(
            horizon_days, scenario_count
        )
        _write_json(
            fixtures_dir / "forecast_request.json",
            forecast_request.model_dump(mode="json"),
        )
        _write_json(
            fixtures_dir / "intervention_request.json",
            intervention_request.model_dump(mode="json"),
        )

        torch.manual_seed(20260725)
        forecast_response = run_forecast_mini(
            loaded,
            snapshot=forecast_request.snapshot,
            horizon_days=horizon_days,
            scenario_count=scenario_count,
            request_id=forecast_request.request_id,
            forecast_id="forecast_fixture_mini_20260725_122238",
        )
        torch.manual_seed(20260725)
        intervention_response = run_forecast_mini(
            loaded,
            snapshot=intervention_request.snapshot,
            horizon_days=horizon_days,
            scenario_count=scenario_count,
            request_id=intervention_request.request_id,
            forecast_id="intervention_fixture_mini_20260725_122238",
            intervention=intervention_request.intervention,
        )
        fixture_generated_at = datetime(
            2026, 7, 25, 22, 0, tzinfo=timezone.utc
        )
        forecast_response = forecast_response.model_copy(
            update={
                "generated_at": fixture_generated_at,
                "valid_until": fixture_generated_at + timedelta(hours=1),
            }
        )
        intervention_response = intervention_response.model_copy(
            update={
                "generated_at": fixture_generated_at,
                "valid_until": fixture_generated_at + timedelta(hours=1),
            }
        )
        _write_json(
            fixtures_dir / "forecast_response.json",
            forecast_response.model_dump(mode="json"),
        )
        _write_json(
            fixtures_dir / "intervention_response.json",
            intervention_response.model_dump(mode="json"),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir", nargs="?", default="integration/generated")
    parser.add_argument("--checkpoint-dir", type=Path)
    args = parser.parse_args()
    build_bundle(Path(args.out_dir), args.checkpoint_dir)


if __name__ == "__main__":
    main()
