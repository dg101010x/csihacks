# Contract ownership (Section 8)

This package contains JSON schemas, TypeScript types, Python Pydantic models, OpenAPI
definitions, example fixtures, and contract validation tests. **It contains no
application logic or model code.** Both Plan One and Plan Two must jointly approve
changes here.

Field names are `snake_case` in every language binding — the wire format (JSON) is the
source of truth, so Python and TypeScript mirror it exactly rather than using
per-language naming conventions.

Versioning rules:

1. Adding an optional field is a **minor** version change.
2. Removing a field is a **major** version change.
3. Changing the meaning of a field is a **major** version change.
4. Renaming a field is a **major** version change.
5. Adding stricter validation may require a **major** version change.
6. Every API request must include `contract_version`.
7. Every persisted model result must store its original `contract_version`.

## Contracts

| Contract | Owner | Version | Purpose |
|---|---|---|---|
| `FinancialEventV1` | Plan Two | 1.0.0 | One immutable ledger-sourced financial event (Section 9). |
| `HouseholdSnapshotV1` | Plan Two | 1.0.0 | Complete input to every forecast provider (Section 10). |
| `ForecastRequestV1` | Plan Two | 1.0.0 | Request to any forecast provider (mock/deterministic/relieffm) (Section 11). |
| `ForecastResponseV1` | Plan One + Plan Two | 1.0.0 | Response returned by every forecast provider, same shape regardless of provider (Section 12). |
| `InterventionSimulationRequestV1` | Plan Two | 1.0.0 | Request to simulate a candidate intervention package against a base forecast (Section 13). |

Each contract's required/optional fields, validation rules, and migration notes live as
comments directly above the Zod schema in `src/` (TypeScript) and the Pydantic model in
`python/relief_contracts/` (Python) — kept next to the code so they cannot drift from
the implementation. `CHANGELOG.md` in this directory is the version history required by
Section 8, rule 9 ("migration notes").

## Cross-language validation

Per Section 88: the same fixture must pass all three validators.

- `tests/` (Vitest) validates every fixture in `fixtures/` against the Zod schema *and*
  against the hand-authored JSON Schema (via ajv).
- `python/tests/` (pytest) validates every fixture in `fixtures/` against the Pydantic
  model.
