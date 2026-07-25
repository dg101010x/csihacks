"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { ForecastChart } from "@/components/forecast/forecast-chart";
import { EventDetailPanel } from "@/components/forecast/event-detail-panel";
import { SafetySummary } from "@/components/command-center/safety-summary";
import { NextCollisionPanel } from "@/components/command-center/next-collision-panel";
import { ActiveProtections } from "@/components/command-center/active-protections";
import { UpcomingEventsList } from "@/components/command-center/upcoming-events-list";
import { useForecastEnvelope, useRiskWindows, useConstitutionRules } from "@/domain/hooks";
import { LoadingState } from "@relief/design-system";
import type { ForecastPoint } from "@/domain/types";

/**
 * Command Center (Section 6) — replaces the old /dashboard + /demo split.
 * The first viewport answers: is Sarah safe, what's the next risk, when,
 * and what should she do.
 */
export default function CommandCenterPage() {
  const forecast = useForecastEnvelope();
  const riskWindows = useRiskWindows();
  const constitution = useConstitutionRules();
  const [selectedPoint, setSelectedPoint] = useState<ForecastPoint | null>(null);

  const confidenceById = useMemo(() => {
    const map = new Map<string, number>();
    for (const obligation of forecast.data?.snapshot.obligations ?? []) {
      map.set(obligation.obligation_id, obligation.source_confidence);
    }
    return map;
  }, [forecast.data]);

  if (forecast.isLoading || !forecast.data) {
    return (
      <AppShell title="Command Center">
        <LoadingState label="Loading Sarah's financial state…" />
      </AppShell>
    );
  }

  const { envelope, snapshot } = forecast.data;
  const windows = riskWindows.data ?? [];
  const currentBalanceCents = snapshot.accounts.reduce((sum, a) => sum + a.current_balance_cents, 0);
  const nextIncome =
    snapshot.known_future_events
      .filter((e) => e.direction === "inflow")
      .sort((a, b) => a.effective_at.localeCompare(b.effective_at))[0] ?? null;
  const nextObligation =
    [...snapshot.obligations].sort((a, b) => (a.next_due_at ?? "").localeCompare(b.next_due_at ?? ""))[0] ?? null;

  return (
    <AppShell title="Command Center">
      <div className="relative flex flex-col gap-4">
        <SafetySummary
          envelope={envelope}
          riskWindows={windows}
          household={{ currentBalanceCents, nextIncome, nextObligation }}
        />

        <div className="rounded-lg border border-border bg-surface p-4">
          <ForecastChart envelope={envelope} riskWindows={windows} onSelectPoint={setSelectedPoint} />
        </div>

        <NextCollisionPanel window={windows[0] ?? null} obligations={snapshot.obligations} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ActiveProtections reserveCents={envelope.reserve_cents} activeRules={constitution.data?.active ?? []} />
          <UpcomingEventsList envelope={envelope} confidenceById={confidenceById} />
        </div>

        {selectedPoint && <EventDetailPanel point={selectedPoint} onClose={() => setSelectedPoint(null)} />}
      </div>
    </AppShell>
  );
}
