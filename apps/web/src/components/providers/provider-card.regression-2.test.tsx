import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProviderCard } from "./provider-card";
import type { ProviderStatus } from "@/domain/types";

const disconnectedProvider: ProviderStatus = {
  provider_id: "plaid-sandbox",
  display_name: "Plaid Sandbox",
  connection_status: "disconnected",
  accounts_available: 0,
  last_synced_at: "2026-07-25T17:00:00Z",
  supported_actions: ["transaction_sync"],
  unsupported_actions: [],
  approval_requirements: "Not connected.",
  expected_response_time: "N/A",
  pending_requests: 0,
  is_simulated: true,
};

// Regression: FINDING-003 — disconnected providers claimed their data was readable
// Found by /design-review on 2026-07-25
// Report: .gstack/design-reports/design-audit-localhost-2026-07-25.md
describe("ProviderCard connection summary", () => {
  it("asks the user to connect a disconnected source", () => {
    render(<ProviderCard provider={disconnectedProvider} />);

    expect(
      screen.getByText("Connect this source to make its financial data available to Relief."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Relief can read balances and transactions from this source."),
    ).not.toBeInTheDocument();
  });
});
