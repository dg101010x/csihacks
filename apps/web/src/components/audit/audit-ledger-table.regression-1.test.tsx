import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AuditLedgerTable } from "./audit-ledger-table";
import type { AuditRecord } from "@/domain/types";

const record: AuditRecord = {
  id: "audit-1",
  decision_id: "decision-1",
  event_type: "intervention_submitted",
  actor_type: "consumer",
  actor_id: "sarah",
  request_id: "request-1",
  occurred_at: "2026-07-25T17:00:00Z",
  summary: "Sarah submitted an intervention.",
  reason: "Consumer approval.",
  evidence: [],
  before_state: null,
  after_state: "submitted",
  related_model_version: null,
  related_data_sources: [],
  related_constitution_rule_id: null,
};

// Regression: ISSUE-002 — audit details were only reachable with a pointer
// Found by /qa on 2026-07-25
// Report: .gstack/qa-reports/qa-report-localhost-2026-07-25.md
describe("AuditLedgerTable accessibility", () => {
  it("opens an audit record from a semantic keyboard-operable button", () => {
    const onSelect = vi.fn();
    render(<AuditLedgerTable records={[record]} onSelect={onSelect} />);

    const detailsButton = screen.getByRole("button", {
      name: "View details for intervention submitted",
    });
    fireEvent.click(detailsButton);

    expect(onSelect).toHaveBeenCalledWith(record);
  });
});
