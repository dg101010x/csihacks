"use client";

import { AppShell } from "@/components/shell/app-shell";
import { BalanceSummary } from "@/components/financial/balance-summary";
import { ResilienceScoreCard } from "@/components/financial/resilience-score-card";
import { RiskSummaryCard } from "@/components/financial/risk-summary-card";
import { UpcomingObligationsCard } from "@/components/financial/upcoming-obligations-card";
import { DataFreshnessCard } from "@/components/financial/data-freshness-card";
import { CashFlowTimeline } from "@/components/timeline/cash-flow-timeline";
import { useHouseholdSnapshot, useResilienceScore, useForecast, useTriggerShock, useResetDemo } from "@/hooks/use-household";
import { Button, LoadingState } from "@relief/design-system";
import { formatCents } from "@/lib/format";

/**
 * Section 16.3 demonstration journey / Section 17 /demo route. Phase B DoD:
 * the complete baseline scenario renders from static fixtures (served here
 * through MSW, Section 24) and the shock control recalculates the timeline.
 */
export default function DemoPage() {
  const snapshot = useHouseholdSnapshot();
  const resilience = useResilienceScore();
  const forecast = useForecast();
  const shock = useTriggerShock();
  const reset = useResetDemo();

  const isShocked = snapshot.data?.data.snapshot_id === "snap_sarah_shock";
  const isLoading = snapshot.isLoading || resilience.isLoading || forecast.isLoading;

  return (
    <AppShell title="Shock simulator">
      <div className="flex flex-col gap-6">
        <div className="flex items-center justify-between rounded-lg border border-border bg-surface p-4">
          <div>
            <p className="text-sm font-medium text-foreground">
              {isShocked ? "Paycheck reduced by $380.00" : "Baseline — no shock applied"}
            </p>
            <p className="text-xs text-muted-foreground">
              Reduces Sarah&apos;s most recent paycheck from {formatCents(210000)} to {formatCents(172000)} and
              recalculates the timeline (Section 16.3).
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => reset.mutate()} disabled={!isShocked || reset.isPending}>
              Reset
            </Button>
            <Button
              variant="destructive"
              size="sm"
              isLoading={shock.isPending}
              disabled={isShocked}
              onClick={() => shock.mutate()}
            >
              Reduce paycheck by $380.00
            </Button>
          </div>
        </div>

        {isLoading || !snapshot.data || !resilience.data || !forecast.data ? (
          <LoadingState label="Loading household state…" />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <BalanceSummary accounts={snapshot.data.data.accounts} />
              <ResilienceScoreCard score={resilience.data.data} />
              <DataFreshnessCard generatedAt={forecast.data.data.generated_at} isStale={forecast.data.data.is_stale} />
            </div>

            <div className="rounded-lg border border-border bg-surface p-4">
              <CashFlowTimeline forecast={forecast.data.data} />
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <UpcomingObligationsCard obligations={snapshot.data.data.obligations} />
              <RiskSummaryCard forecast={forecast.data.data} />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
