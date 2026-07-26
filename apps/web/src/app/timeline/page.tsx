"use client";

import { useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { ForecastChart } from "@/components/forecast/forecast-chart";
import { EventDetailPanel } from "@/components/forecast/event-detail-panel";
import { RiskWindowList } from "@/components/forecast/risk-window-list";
import { useForecastEnvelope, useRiskWindows } from "@/domain/hooks";
import { LoadingState } from "@relief/design-system";
import type { ForecastPoint } from "@/domain/types";

/**
 * Timeline (Section 7) — the complete forecasted event stream and liquidity
 * trajectory. Every event is selectable and opens the same detail panel
 * used on Command Center; risk windows are both shaded on the chart and
 * listed explicitly below it.
 */
export default function TimelinePage() {
  const forecast = useForecastEnvelope();
  const riskWindows = useRiskWindows();
  const [selectedPoint, setSelectedPoint] = useState<ForecastPoint | null>(null);

  if (forecast.isLoading || !forecast.data) {
    return (
      <AppShell title="Timeline">
        <LoadingState label="Loading forecast…" />
      </AppShell>
    );
  }

  const { envelope } = forecast.data;
  const windows = riskWindows.data ?? [];

  return (
    <AppShell title="Timeline">
      <div className="relative flex flex-col gap-4">
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="mb-2 text-xs text-muted-foreground">
            Forecast confidence {Math.round(envelope.evidence.confidence * 100)}%
          </p>
          <ForecastChart envelope={envelope} riskWindows={windows} height={420} onSelectPoint={setSelectedPoint} />
        </div>

        <RiskWindowList windows={windows} />

        {selectedPoint && <EventDetailPanel point={selectedPoint} onClose={() => setSelectedPoint(null)} />}
      </div>
    </AppShell>
  );
}
