import { http, HttpResponse } from "msw";
import {
  sarahBaseline,
  sarahIncomeShock,
  sarahInterventionOptions,
  sarahProviderApproval,
  sarahCompletedCase,
  sarahConstitution,
  sarahProviderStatus,
  sarahDataTrust,
} from "../src/index";

/**
 * Mock Service Worker handlers (Section 24). Backs the complete
 * demonstration before the real API exists — front end development must not
 * wait for backend implementation (Section 7, item 5; Section 24).
 *
 * In-memory only: `state.shocked` / `state.caseStatus` let the demo walk
 * through the consumer journey (Section 16.1) across requests within one
 * browser session. Reset on page reload — there is no persistence here by
 * design, this is a fixture server, not the real API.
 */
const state = {
  shocked: false,
  plaidConnected: false,
  caseStatus: "not_started" as "not_started" | "consumer_approved" | "provider_approved" | "completed",
};

function envelope<T>(data: T, requestId: string) {
  return {
    request_id: requestId,
    data,
    errors: [],
    warnings: [],
    metadata: {
      contract_version: "1.0.0",
      generated_at: new Date().toISOString(),
    },
  };
}

export const handlers = [
  // Accounts
  http.get("*/v1/accounts", () => {
    const snapshot = state.shocked ? sarahIncomeShock.household_snapshot : sarahBaseline.household_snapshot;
    return HttpResponse.json(envelope(snapshot.accounts, "req_accounts_01"));
  }),

  // Transactions (recent + known future events, per the ledger's financial_events shape)
  http.get("*/v1/accounts/:accountId/events", () => {
    const snapshot = state.shocked ? sarahIncomeShock.household_snapshot : sarahBaseline.household_snapshot;
    return HttpResponse.json(
      envelope([...snapshot.recent_events, ...snapshot.known_future_events], "req_events_01"),
    );
  }),

  // Household snapshot + resilience score
  http.get("*/v1/households/current/snapshot", () => {
    const fixture = state.shocked ? sarahIncomeShock : sarahBaseline;
    return HttpResponse.json(envelope(fixture.household_snapshot, "req_snapshot_01"));
  }),
  http.get("*/v1/resilience/current", () => {
    const fixture = state.shocked ? sarahIncomeShock : sarahBaseline;
    return HttpResponse.json(envelope(fixture.resilience_score, "req_resilience_01"));
  }),

  // Forecasts (Section 31.4) — generates a forecast for the household's
  // *current* state. Does not itself mutate state; see /v1/demo/shock below
  // for the Section 16.3 shock simulator, a demo-only action.
  http.post("*/v1/forecasts", () => {
    const fixture = state.shocked ? sarahIncomeShock : sarahBaseline;
    return HttpResponse.json(envelope(fixture.forecast, "req_forecast_01"));
  }),
  http.get("*/v1/forecasts/:forecastId", ({ params }) => {
    const fixture = params.forecastId === "forecast_sarah_shock" ? sarahIncomeShock : sarahBaseline;
    return HttpResponse.json(envelope(fixture.forecast, "req_forecast_get_01"));
  }),

  // Demo-only: the Section 16.3 shock simulator (/demo route, Section 17).
  // Not part of the Section 31 production API surface.
  http.post("*/v1/demo/shock", () => {
    state.shocked = true;
    return HttpResponse.json(envelope(sarahIncomeShock, "req_demo_shock_01"));
  }),
  http.post("*/v1/demo/reset", () => {
    resetHandlerState();
    return HttpResponse.json(envelope(sarahBaseline, "req_demo_reset_01"));
  }),

  // Interventions
  http.post("*/v1/interventions/generate", () => {
    return HttpResponse.json(envelope(sarahInterventionOptions.candidates, "req_generate_01"));
  }),
  http.get("*/v1/interventions", () => {
    return HttpResponse.json(envelope(sarahInterventionOptions.candidates, "req_interventions_01"));
  }),
  http.get("*/v1/interventions/:interventionId", ({ params }) => {
    const candidate = sarahInterventionOptions.candidates.find((c) => c.package_id === params.interventionId);
    return HttpResponse.json(envelope(candidate ?? null, "req_intervention_get_01"));
  }),

  // Approvals
  http.post("*/v1/interventions/:interventionId/approve", () => {
    state.caseStatus = "consumer_approved";
    return HttpResponse.json(envelope(sarahProviderApproval, "req_consumer_approve_01"));
  }),
  http.post("*/v1/provider/cases/:caseId/approve", () => {
    state.caseStatus = "provider_approved";
    return HttpResponse.json(envelope(sarahCompletedCase, "req_provider_approve_01"));
  }),
  http.get("*/v1/provider/cases/:caseId", () => {
    const data = state.caseStatus === "provider_approved" || state.caseStatus === "completed"
      ? sarahCompletedCase
      : sarahProviderApproval;
    return HttpResponse.json(envelope(data, "req_provider_case_01"));
  }),

  // Audit data
  http.get("*/v1/audit/:decisionId", () => {
    return HttpResponse.json(envelope(sarahCompletedCase.audit_trail, "req_audit_01"));
  }),

  // Provider policies
  http.get("*/v1/constitution", () => {
    const fixture = state.shocked ? sarahIncomeShock : sarahBaseline;
    return HttpResponse.json(envelope(fixture.household_snapshot.consumer_constitution, "req_constitution_01"));
  }),
  http.get("*/v1/constitution/rules", () => {
    return HttpResponse.json(envelope(sarahConstitution, "req_constitution_rules_01"));
  }),

  // Integration status
  http.get("*/v1/integrations/status", () => {
    return HttpResponse.json(
      envelope(
        [
          { provider: "synthetic_wells_fargo", status: "connected", is_simulated: true, last_synced_at: new Date().toISOString() },
          {
            provider: "plaid_sandbox",
            status: state.plaidConnected ? "connected" : "not_connected",
            is_simulated: true,
            last_synced_at: state.plaidConnected ? new Date().toISOString() : null,
          },
        ],
        "req_integrations_01",
      ),
    );
  }),
  http.post("*/v1/integrations/plaid/sandbox/connect", () => {
    state.plaidConnected = true;
    return HttpResponse.json(
      envelope(
        {
          provider: "plaid_sandbox",
          connection_status: "connected",
          accounts_available: 12,
          events_synchronized: 0,
          last_synced_at: new Date().toISOString(),
          is_simulated: true,
          forecast_input_enabled: false,
        },
        "req_plaid_connect_01",
      ),
    );
  }),

  // Provider status (Providers page)
  http.get("*/v1/providers/status", () => {
    const providers = sarahProviderStatus.providers.map((provider) =>
      provider.provider_id === "plaid_sandbox" && state.plaidConnected
        ? {
            ...provider,
            connection_status: "connected" as const,
            accounts_available: 12,
            last_synced_at: new Date().toISOString(),
            approval_requirements: "Connected to Plaid Sandbox; data is simulated and read-only.",
            expected_response_time: "Live sandbox synchronization",
          }
        : provider,
    );
    return HttpResponse.json(envelope(providers, "req_providers_status_01"));
  }),

  // Data trust (Data page)
  http.get("*/v1/data/trust", () => {
    return HttpResponse.json(envelope(sarahDataTrust.sources, "req_data_trust_01"));
  }),
];

/** Resets in-memory demo state between test runs / Storybook stories. */
export function resetHandlerState() {
  state.shocked = false;
  state.plaidConnected = false;
  state.caseStatus = "not_started";
}
