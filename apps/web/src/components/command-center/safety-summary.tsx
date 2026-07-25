"use client";

import { Card, CardContent } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import { useNow } from "@/hooks/use-now";
import type { ForecastEnvelope, HouseholdSnapshotSummary } from "./types";
import type { RiskWindow } from "@/domain/types";

/**
 * Section 6.1 — the first thing Command Center says. Answers "is Sarah
 * financially safe" in one sentence before anything else on the page.
 */
export function SafetySummary({
  envelope,
  riskWindows,
  household,
}: {
  envelope: ForecastEnvelope;
  riskWindows: RiskWindow[];
  household: HouseholdSnapshotSummary;
}) {
  const now = useNow();
  const firstRisk = riskWindows[0];
  const headline = firstRisk
    ? `Reserve risk begins ${relativeDay(firstRisk.start_date, now)}`
    : `Protected through ${formatDate(envelope.points.at(-1)?.date ?? "")}`;

  const nextIncome = household.nextIncome;
  const nextObligation = household.nextObligation;

  return (
    <Card>
      <CardContent className="flex flex-col gap-5 p-6">
        <div>
          <p className="text-2xl font-semibold text-foreground sm:text-3xl">{headline}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Forecast confidence {Math.round(envelope.evidence.confidence * 100)}%
            {envelope.evidence.freshness !== "current" && ` · data ${envelope.evidence.freshness}`}
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <Metric label="Available balance" value={formatCents(household.currentBalanceCents)} />
          <Metric label="Essential reserve" value={formatCents(envelope.reserve_cents)} />
          <Metric
            label="Safe liquidity runway"
            value={firstRisk ? `${daysUntil(firstRisk.start_date, now)} days` : `${envelope.horizon_days}+ days`}
          />
          <Metric
            label="Next income"
            value={nextIncome ? formatCents(nextIncome.amount_cents) : "—"}
            hint={nextIncome ? formatDate(nextIncome.effective_at) : undefined}
          />
        </dl>
        {nextObligation && (
          <p className="text-sm text-muted-foreground">
            Next major obligation: <span className="text-foreground">{nextObligation.display_name}</span> —{" "}
            {formatCents(nextObligation.scheduled_amount_cents)} due{" "}
            {nextObligation.next_due_at ? formatDate(nextObligation.next_due_at) : "soon"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="font-mono text-lg font-semibold tabular-nums text-foreground">{value}</dd>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

function daysUntil(dateIso: string, now: number): number {
  const diff = new Date(dateIso).getTime() - now;
  return Math.max(0, Math.round(diff / 86_400_000));
}

function relativeDay(dateIso: string, now: number): string {
  const days = daysUntil(dateIso, now);
  if (days === 0) return "today";
  if (days === 1) return "in 1 day";
  return `in ${days} days`;
}
