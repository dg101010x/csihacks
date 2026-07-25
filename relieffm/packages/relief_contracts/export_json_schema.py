"""Export JSON Schema for every contract model.

Partner (Plan Two) generates TypeScript types from these. Run:
    python -m relief_contracts.export_json_schema [out_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import schemas

MODELS = [
    schemas.HouseholdSnapshotV1,
    schemas.ForecastRequestV1,
    schemas.ForecastResponseV1,
    schemas.InterventionSimulationRequestV1,
    schemas.ModelMetadataV1,
]


def main(out_dir: str = "packages/relief_contracts/json_schema") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for model in MODELS:
        schema = model.model_json_schema()
        path = out / f"{model.__name__}.schema.json"
        path.write_text(json.dumps(schema, indent=2, sort_keys=True))
        print(f"wrote {path}")


if __name__ == "__main__":
    main(*sys.argv[1:])
