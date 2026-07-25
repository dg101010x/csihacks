import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import Ajv2020 from "ajv/dist/2020";
import addFormats from "ajv-formats";

import {
  FinancialEventV1,
  HouseholdSnapshotV1,
  ForecastRequestV1,
  ForecastResponseV1,
  InterventionSimulationRequestV1,
} from "../src";

const fixturesDir = join(__dirname, "..", "fixtures");
const schemaDir = join(__dirname, "..", "json_schema");

function loadFixture(name: string) {
  return JSON.parse(readFileSync(join(fixturesDir, name), "utf-8"));
}

function loadSchema(name: string) {
  return JSON.parse(readFileSync(join(schemaDir, name), "utf-8"));
}

const ajv = new Ajv2020({ strict: true });
addFormats(ajv);
ajv.addSchema(loadSchema("definitions.v1.schema.json"));
ajv.addSchema(loadSchema("financial_event.v1.schema.json"));
ajv.addSchema(loadSchema("household_snapshot.v1.schema.json"));
ajv.addSchema(loadSchema("forecast_request.v1.schema.json"));
ajv.addSchema(loadSchema("forecast_response.v1.schema.json"));
ajv.addSchema(loadSchema("intervention_simulation_request.v1.schema.json"));

const cases = [
  {
    label: "FinancialEventV1",
    fixture: "financial_event.v1.example.json",
    zod: FinancialEventV1,
    schemaId: "https://relief.dev/schemas/financial_event.v1.schema.json",
  },
  {
    label: "HouseholdSnapshotV1",
    fixture: "household_snapshot.v1.example.json",
    zod: HouseholdSnapshotV1,
    schemaId: "https://relief.dev/schemas/household_snapshot.v1.schema.json",
  },
  {
    label: "ForecastRequestV1",
    fixture: "forecast_request.v1.example.json",
    zod: ForecastRequestV1,
    schemaId: "https://relief.dev/schemas/forecast_request.v1.schema.json",
  },
  {
    label: "ForecastResponseV1",
    fixture: "forecast_response.v1.example.json",
    zod: ForecastResponseV1,
    schemaId: "https://relief.dev/schemas/forecast_response.v1.schema.json",
  },
  {
    label: "InterventionSimulationRequestV1",
    fixture: "intervention_simulation_request.v1.example.json",
    zod: InterventionSimulationRequestV1,
    schemaId: "https://relief.dev/schemas/intervention_simulation_request.v1.schema.json",
  },
] as const;

describe("contract fixtures validate against Zod and JSON Schema (Section 88)", () => {
  for (const { label, fixture, zod, schemaId } of cases) {
    it(`${label}: ${fixture} passes Zod`, () => {
      const data = loadFixture(fixture);
      const result = zod.safeParse(data);
      if (!result.success) {
        throw new Error(`${label} Zod validation failed: ${result.error.message}`);
      }
      expect(result.success).toBe(true);
    });

    it(`${label}: ${fixture} passes JSON Schema`, () => {
      const data = loadFixture(fixture);
      const validate = ajv.getSchema(schemaId);
      if (!validate) throw new Error(`No compiled schema for ${schemaId}`);
      const valid = validate(data);
      if (!valid) {
        throw new Error(`${label} JSON Schema validation failed: ${JSON.stringify(validate.errors)}`);
      }
      expect(valid).toBe(true);
    });
  }
});

describe("contract version discipline (Section 8)", () => {
  it("rejects a malformed contract_version", () => {
    const data = loadFixture("financial_event.v1.example.json");
    data.contract_version = "not-a-version";
    const result = FinancialEventV1.safeParse(data);
    expect(result.success).toBe(false);
  });

  it("rejects a ForecastResponseV1 with model_metadata set on a non-relieffm provider", () => {
    const data = loadFixture("forecast_response.v1.example.json");
    data.model_metadata = { model_version: "1.0.0", calibration_version: null, inference_latency_ms: 10 };
    const result = ForecastResponseV1.safeParse(data);
    expect(result.success).toBe(false);
  });
});
