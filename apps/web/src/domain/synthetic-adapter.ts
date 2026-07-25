import type {
  ForecastResponseV1,
  HouseholdSnapshotV1,
  ObligationV1,
} from "@relief/contracts";
import type {
  InterventionCandidateV1,
  ConstitutionRuleV1,
  ProviderCaseV1,
  AuditEventV1,
  ProviderStatusV1,
  DataTrustV1,
} from "@relief/test-fixtures";
import { apiGet, apiPost } from "@/lib/api";
import type {
  AuditRecord,
  ConstitutionSimulationResult,
  DataTrust,
  ForecastEnvelope,
  ForecastPoint,
  InterventionPackage,
  ModelEvidence,
  ProviderAction,
  ProviderStatus,
  RiskWindow,
  ScenarioDefinition,
  ScenarioDelta,
  ScenarioResult,
} from "./types";

/**
 * The synthetic adapter (Section 14 of the redesign brief). Backed today by
 * @relief/test-fixtures over MSW; talks to the same REST shape a live
 * ReliefFM-backed adapter would. This is the only file that should ever
 * change when Plan One ships live endpoints — see docs/ui_architecture.md.
 */

function evidenceFrom(forecast: Pick<ForecastResponseV1, "confidence" | "generated_at" | "provider_version" | "is_stale">): ModelEvidence {
  return {
    model_version: forecast.provider_version,
    confidence: forecast.confidence,
    generated_at: forecast.generated_at,
    source_refs: ["synthetic_wells_fargo"],
    freshness: forecast.is_stale ? "stale" : "current",
    status: "simulated",
  };
}

/**
 * Expands the sparse `daily_summary` (3 points in the underlying fixtures)
 * into one point per day across the full horizon, replaying known events
 * day by day. This is what makes the "existing three point line chart"
 * finding in ui_audit.md go away — every consumer of ForecastEnvelope gets
 * a real daily series, not a hand-authored gap.
 */
function expandDailySeries(
  forecast: ForecastResponseV1,
  snapshot: HouseholdSnapshotV1,
  horizonDays: number,
): ForecastPoint[] {
  const startDate = new Date(forecast.trajectories[0]?.event_date ?? forecast.generated_at);
  startDate.setUTCHours(0, 0, 0, 0);
  // Balance the day before the forecast's first known trajectory point.
  let runningBalance = (forecast.trajectories[0]?.starting_balance_cents ?? 0);

  const knownByDate = new Map(forecast.daily_summary.map((d) => [d.event_date, d]));
  const eventsByDate = new Map<string, typeof snapshot.known_future_events>();
  for (const event of snapshot.known_future_events) {
    const date = event.effective_at.slice(0, 10);
    eventsByDate.set(date, [...(eventsByDate.get(date) ?? []), event]);
  }

  const knownDates = forecast.daily_summary.map((d) => d.event_date).sort();
  const lastKnown = knownDates.at(-1);

  const points: ForecastPoint[] = [];
  for (let i = 0; i < horizonDays; i++) {
    const date = new Date(startDate);
    date.setUTCDate(date.getUTCDate() + i);
    const iso = date.toISOString().slice(0, 10);

    const dayEvents = eventsByDate.get(iso) ?? [];
    for (const event of dayEvents) {
      runningBalance += event.direction === "inflow" ? event.amount_cents : -event.amount_cents;
    }

    const known = knownByDate.get(iso);
    let lower: number;
    let upper: number;
    let probability: number;

    if (known) {
      lower = known.lower_ending_balance_cents;
      upper = known.upper_ending_balance_cents;
      probability = known.reserve_violation_probability;
      runningBalance = known.median_ending_balance_cents;
    } else if (lastKnown && iso > lastKnown) {
      // Past the last modeled point: no further known events expected in
      // this demo horizon, so hold the balance and widen the band gently —
      // uncertainty grows the further out the forecast reaches.
      const daysPast = Math.floor((date.getTime() - new Date(lastKnown).getTime()) / 86_400_000);
      const bandWidth = Math.min(0.15, 0.02 + daysPast * 0.01);
      lower = Math.round(runningBalance * (1 - bandWidth));
      upper = Math.round(runningBalance * (1 + bandWidth));
      probability = 0.02;
    } else {
      // Between the forecast start and the first modeled point.
      const band = Math.round(Math.abs(runningBalance) * 0.03);
      lower = runningBalance - band;
      upper = runningBalance + band;
      probability = 0.05;
    }

    points.push({
      date: iso,
      median_balance_cents: runningBalance,
      lower_balance_cents: lower,
      upper_balance_cents: upper,
      reserve_violation_probability: probability,
      events: dayEvents,
      is_risk: probability >= 0.5 || runningBalance < (forecast.trajectories[0]?.essential_reserve_cents ?? 0),
    });
  }
  return points;
}

export async function fetchForecastEnvelope(horizonDays = 30): Promise<{ envelope: ForecastEnvelope; snapshot: HouseholdSnapshotV1 }> {
  const [snapshotRes, forecastRes] = await Promise.all([
    apiGet<HouseholdSnapshotV1>("/v1/households/current/snapshot"),
    apiPost<ForecastResponseV1>("/v1/forecasts"),
  ]);
  const snapshot = snapshotRes.data;
  const forecast = forecastRes.data;
  const reserveCents = forecast.trajectories[0]?.essential_reserve_cents ?? 0;

  const envelope: ForecastEnvelope = {
    id: forecast.forecast_id,
    provider: forecast.provider,
    horizon_days: horizonDays,
    reserve_cents: reserveCents,
    points: expandDailySeries(forecast, snapshot, horizonDays),
    distress_probabilities: forecast.distress_probabilities,
    reason_factors: forecast.reason_factors,
    valid_until: forecast.valid_until,
    evidence: evidenceFrom(forecast),
    scenario_active: snapshot.snapshot_id !== "snap_sarah_baseline",
  };

  return { envelope, snapshot };
}

export function deriveRiskWindows(
  envelope: ForecastEnvelope,
  snapshot: { obligations: Array<Pick<ObligationV1, "obligation_id" | "display_name">> },
): RiskWindow[] {
  const windows: RiskWindow[] = [];
  let current: ForecastPoint[] | null = null;

  const flush = () => {
    if (!current || current.length === 0) return;
    const lowest = current.reduce((min, p) => Math.min(min, p.median_balance_cents), Infinity);
    const causalIds = new Set<string>();
    for (const point of current) {
      for (const event of point.events) {
        if (event.direction === "outflow" && event.obligation_id) causalIds.add(event.obligation_id);
      }
    }
    const obligationNames = [...causalIds]
      .map((id) => snapshot.obligations.find((o) => o.obligation_id === id)?.display_name)
      .filter((name): name is string => Boolean(name));

    windows.push({
      id: `risk_${current[0]!.date}`,
      start_date: current[0]!.date,
      end_date: current.at(-1)!.date,
      kind: "essential_reserve_violation",
      probability: Math.max(...current.map((p) => p.reserve_violation_probability)),
      projected_lowest_balance_cents: lowest,
      causal_obligation_ids: [...causalIds],
      description:
        obligationNames.length > 0
          ? `${obligationNames.join(" and ")} reduce available liquidity below the essential reserve.`
          : "Available liquidity is projected to fall below the essential reserve.",
      evidence: envelope.evidence,
    });
    current = null;
  };

  for (const point of envelope.points) {
    if (point.is_risk) {
      current = current ?? [];
      current.push(point);
    } else {
      flush();
    }
  }
  flush();

  return windows;
}

export async function fetchScenarioBaseline(): Promise<ForecastEnvelope> {
  await apiPost("/v1/demo/reset");
  const { envelope } = await fetchForecastEnvelope();
  return envelope;
}

export async function applyScenario(scenario: ScenarioDefinition): Promise<ScenarioResult> {
  const baseline = (await fetchForecastEnvelope()).envelope;
  await apiPost("/v1/demo/shock");
  const activeResult = await fetchForecastEnvelope();
  const active = activeResult.envelope;
  const riskWindows = deriveRiskWindows(active, activeResult.snapshot);

  const baselineLowest = Math.min(...baseline.points.map((p) => p.median_balance_cents));
  const activeLowest = Math.min(...active.points.map((p) => p.median_balance_cents));
  const baselineDaysBelow = baseline.points.filter((p) => p.median_balance_cents < baseline.reserve_cents).length;
  const activeDaysBelow = active.points.filter((p) => p.median_balance_cents < active.reserve_cents).length;
  const recovery = active.points.find(
    (p, i) => i > 0 && p.median_balance_cents >= active.reserve_cents && active.points[i - 1]!.median_balance_cents < active.reserve_cents,
  );

  const deltas: ScenarioDelta = {
    lowest_balance_delta_cents: activeLowest - baselineLowest,
    days_below_reserve_delta: activeDaysBelow - baselineDaysBelow,
    missed_obligation_probability_delta:
      active.distress_probabilities.missed_obligation - baseline.distress_probabilities.missed_obligation,
    negative_balance_probability_delta:
      active.distress_probabilities.negative_balance - baseline.distress_probabilities.negative_balance,
    added_intervention_cost_cents: 0,
    recovery_date: recovery?.date ?? null,
  };

  return { scenario, baseline, active, deltas, riskWindows };
}

export async function resetScenario(): Promise<void> {
  await apiPost("/v1/demo/reset");
}

function packageEvidence(): ModelEvidence {
  return {
    model_version: "elasticity-v1.0.0",
    confidence: 0.85,
    generated_at: new Date().toISOString(),
    source_refs: ["deterministic-1.0.0"],
    freshness: "current",
    status: "simulated",
  };
}

export async function fetchInterventionPackages(): Promise<InterventionPackage[]> {
  const res = await apiPost<InterventionCandidateV1[]>("/v1/interventions/generate");
  return res.data.map((candidate) => ({
    id: candidate.package_id,
    label: candidate.label,
    description: candidate.description,
    actions: candidate.actions,
    added_cost_cents: candidate.added_cost_cents,
    new_minimum_balance_cents: candidate.new_minimum_balance_cents,
    remaining_risk: candidate.remaining_risk,
    required_approvals: candidate.required_approvals,
    user_effort: candidate.user_effort,
    provider_acceptance_probability: candidate.provider_acceptance_probability,
    reversibility: candidate.reversibility,
    constitution_compatible: candidate.constitution_compatible,
    ranking_reason: candidate.ranking_reason,
    stage: "review",
    evidence: { ...packageEvidence(), confidence: candidate.confidence },
  }));
}

export async function approveIntervention(packageId: string): Promise<ProviderAction | null> {
  const res = await apiPost<{ provider_case: ProviderCaseV1 }>(`/v1/interventions/${packageId}/approve`);
  const providerCase = res.data.provider_case;
  if (!providerCase) return null;
  return {
    id: providerCase.case_id,
    provider_id: providerCase.provider_id,
    provider_display_name: providerCase.provider_id === "prov_auto_lender" ? "Auto Lender" : providerCase.provider_id,
    action_type: "split_payment",
    status: providerCase.status,
    consumer_impact_summary: providerCase.consumer_impact_summary,
    provider_impact_summary: providerCase.provider_impact_summary,
    policy_reference: providerCase.policy_reference,
  };
}

export async function approveProviderCase(caseId: string): Promise<void> {
  await apiPost(`/v1/provider/cases/${caseId}/approve`);
}

export async function fetchConstitutionRules(): Promise<{ active: ConstitutionRuleV1[]; starters: ConstitutionRuleV1[] }> {
  const res = await apiGet<{ rules: ConstitutionRuleV1[]; starter_rules: ConstitutionRuleV1[] }>("/v1/constitution/rules");
  return { active: res.data.rules, starters: res.data.starter_rules };
}

/**
 * Simulated natural-language rule parsing (no LangChain backend exists
 * yet — Section 63 of the platform spec reserves that for Plan Two's
 * explanation layer). Heuristic keyword matching over the known demo
 * inputs, clearly labeled "simulated interpretation" wherever it's shown.
 */
export function parseConstitutionRule(rawText: string): ConstitutionRuleV1 {
  const lower = rawText.toLowerCase();
  const scope: string[] = [];
  if (/rent|housing/.test(lower)) scope.push("housing");
  if (/grocer/.test(lower)) scope.push("groceries");
  if (/medic|health/.test(lower)) scope.push("medicine");
  if (/transport|car|auto/.test(lower)) scope.push("transportation");
  if (/subscri/.test(lower)) scope.push("subscriptions");
  if (/loan|interest/.test(lower)) scope.push("loans");

  const permitted: string[] = [];
  const prohibited: string[] = [];
  if (/split/.test(lower)) permitted.push("split_payment");
  if (/pause/.test(lower)) permitted.push("pause_subscription");
  if (/never.*interest|no.*interest/.test(lower)) prohibited.push("term_extension_with_interest");
  if (/never delay rent|never.*rent/.test(lower)) prohibited.push("delay_rent_without_confirmation");

  const amountMatch = lower.match(/\$?(\d+(?:\.\d{2})?)/);
  const maxImpact = amountMatch ? Math.round(parseFloat(amountMatch[1]!) * 100) : null;

  const alwaysAsk = /\bask/.test(lower) || /confirm/.test(lower);

  return {
    // Date.now() alone can collide across rapid successive calls (e.g. two
    // rules parsed in the same test, or the same UI interaction); add a
    // random suffix so rule_id is always unique.
    rule_id: `draft_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    status: "draft",
    raw_text: rawText,
    trigger: scope.length > 0 ? `Any candidate intervention touching: ${scope.join(", ")}.` : "Any candidate intervention.",
    scope: scope.length > 0 ? scope : ["all"],
    permitted_actions: permitted,
    prohibited_actions: prohibited,
    approval_requirement: alwaysAsk ? "always_ask" : "consumer_confirmation",
    maximum_monetary_impact_cents: maxImpact,
    expiration: null,
    priority: 5,
    exceptions: [],
    confidence: 0.6 + (scope.length > 0 ? 0.1 : 0) + (permitted.length + prohibited.length > 0 ? 0.1 : 0),
    created_at: new Date().toISOString(),
  };
}

export function simulateConstitutionRule(
  rule: ConstitutionRuleV1,
  packages: InterventionPackage[],
  existingRules: ConstitutionRuleV1[] = [],
): ConstitutionSimulationResult {
  const allowed: string[] = [];
  const blocked: string[] = [];
  for (const pkg of packages) {
    const touchesProhibited = pkg.actions.some((a) => rule.prohibited_actions.includes(a.action_type));
    if (touchesProhibited || !pkg.constitution_compatible) {
      blocked.push(pkg.id);
    } else {
      allowed.push(pkg.id);
    }
  }

  // A conflict is any action this rule permits that an existing rule
  // prohibits, or vice versa.
  const conflicts: ConstitutionSimulationResult["conflicts"] = [];
  for (const existing of existingRules) {
    if (existing.rule_id === rule.rule_id) continue;
    const permittedButProhibited = rule.permitted_actions.filter((a) => existing.prohibited_actions.includes(a));
    const prohibitedButPermitted = rule.prohibited_actions.filter((a) => existing.permitted_actions.includes(a));
    const overlap = [...permittedButProhibited, ...prohibitedButPermitted];
    if (overlap.length > 0) {
      conflicts.push({
        with_rule_id: existing.rule_id,
        description: `Conflicts with an existing rule over: ${overlap.join(", ")}.`,
      });
    }
  }

  return { rule, allowed_package_ids: allowed, blocked_package_ids: blocked, conflicts };
}

export async function fetchAuditRecords(): Promise<AuditRecord[]> {
  const res = await apiGet<AuditEventV1[]>("/v1/audit/case_sarah_01");
  return res.data.map((event) => ({
    id: event.event_id,
    decision_id: event.decision_id,
    event_type: event.event_type,
    actor_type: event.actor_type,
    actor_id: event.actor_id,
    request_id: event.request_id,
    occurred_at: event.occurred_at,
    summary: event.summary,
    reason: event.reason,
    evidence: event.evidence,
    before_state: event.before_state,
    after_state: event.after_state,
    related_model_version: event.related_model_version,
    related_data_sources: event.related_data_sources,
    related_constitution_rule_id: event.related_constitution_rule_id,
  }));
}

export async function fetchProviderStatus(): Promise<ProviderStatus[]> {
  const res = await apiGet<ProviderStatusV1[]>("/v1/providers/status");
  return res.data;
}

export async function fetchDataTrust(): Promise<DataTrust[]> {
  const res = await apiGet<DataTrustV1[]>("/v1/data/trust");
  return res.data;
}
