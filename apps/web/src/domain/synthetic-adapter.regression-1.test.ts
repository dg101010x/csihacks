import { describe, expect, it } from "vitest";
import { parseConstitutionRule } from "./synthetic-adapter";

// Regression: ISSUE-001 — "automatically" was parsed as an auto-loan scope
// Found by /qa on 2026-07-25
// Report: .gstack/qa-reports/qa-report-localhost-2026-07-25.md
describe("parseConstitutionRule automatic approval", () => {
  it("keeps an automatic subscription rule scoped to subscriptions", () => {
    const rule = parseConstitutionRule(
      "You may pause subscriptions under $25.00 automatically when my essential reserve is at risk.",
    );

    expect(rule.scope).toEqual(["subscriptions"]);
    expect(rule.permitted_actions).toEqual(["pause_subscription"]);
    expect(rule.approval_requirement).toBe("none");
    expect(rule.maximum_monetary_impact_cents).toBe(2500);
  });

  it("still recognizes auto loans as transportation", () => {
    const rule = parseConstitutionRule("Split my auto loan payment when needed.");

    expect(rule.scope).toContain("transportation");
    expect(rule.scope).toContain("loans");
  });
});
