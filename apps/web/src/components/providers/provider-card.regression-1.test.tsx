import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProviderCard } from "./provider-card";
import type { ProviderStatus } from "@/domain/types";

const provider: ProviderStatus = {
  provider_id: "plaid-sandbox",
  display_name: "Plaid Sandbox",
  connection_status: "connected",
  accounts_available: 12,
  last_synced_at: "2026-07-25T17:00:00Z",
  supported_actions: ["transaction_sync"],
  unsupported_actions: ["money_movement"],
  approval_requirements: "Read-only sandbox.",
  expected_response_time: "Instant",
  pending_requests: 0,
  is_simulated: true,
};

// Regression: FINDING-001 — provider cards exposed implementation details before user context
// Found by /design-review on 2026-07-25
// Report: .gstack/design-reports/design-audit-localhost-2026-07-25.md
describe("ProviderCard detail disclosure", () => {
  it("keeps technical fields collapsed until requested", () => {
    render(<ProviderCard provider={provider} />);

    expect(screen.getByText("Relief can read balances and transactions from this source.")).toBeInTheDocument();
    expect(screen.queryByText("transaction_sync")).not.toBeInTheDocument();

    const detailsButton = screen.getByRole("button", { name: "Technical details" });
    expect(detailsButton).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(detailsButton);

    expect(detailsButton).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("transaction_sync")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
  });
});
