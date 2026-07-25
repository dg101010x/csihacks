"use client";

import { AppShell } from "@/components/shell/app-shell";
import { BalanceSummary } from "@/components/financial/balance-summary";
import { ResilienceScoreCard } from "@/components/financial/resilience-score-card";
import { IncomeForecastCard } from "@/components/financial/income-forecast-card";
import { UpcomingObligationsCard } from "@/components/financial/upcoming-obligations-card";
import { RiskSummaryCard } from "@/components/financial/risk-summary-card";
import { DataFreshnessCard } from "@/components/financial/data-freshness-card";
import { useHouseholdSnapshot, useResilienceScore, useForecast } from "@/hooks/use-household";
import { LoadingState } from "@relief/design-system";

/** Section 17 /dashboard, Section 21.2 financial state components. */
export default function DashboardPage() {
  const snapshot = useHouseholdSnapshot();
  const resilience = useResilienceScore();
  const forecast = useForecast();

  if (snapshot.isLoading || resilience.isLoading || forecast.isLoading || !snapshot.data || !resilience.data || !forecast.data) {
    return (
      <AppShell title="Dashboard">
        <LoadingState label="Loading household state…" />
      </AppShell>
    );
  }

  return (
    <AppShell title="Dashboard">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <BalanceSummary accounts={snapshot.data.data.accounts} />
        <ResilienceScoreCard score={resilience.data.data} />
        <IncomeForecastCard knownFutureEvents={snapshot.data.data.known_future_events} />
        <UpcomingObligationsCard obligations={snapshot.data.data.obligations} />
        <RiskSummaryCard forecast={forecast.data.data} />
        <DataFreshnessCard generatedAt={forecast.data.data.generated_at} isStale={forecast.data.data.is_stale} />
      </div>
    </AppShell>
  );
}
