"use client";

import { AppShell } from "@/components/shell/app-shell";
import { CashFlowTimeline } from "@/components/timeline/cash-flow-timeline";
import { useForecast } from "@/hooks/use-household";
import { LoadingState } from "@relief/design-system";

/** Section 17 /timeline, Section 21.3. */
export default function TimelinePage() {
  const forecast = useForecast();

  return (
    <AppShell title="Timeline">
      {forecast.isLoading || !forecast.data ? (
        <LoadingState label="Loading forecast…" />
      ) : (
        <div className="rounded-lg border border-border bg-surface p-4">
          <CashFlowTimeline forecast={forecast.data.data} />
        </div>
      )}
    </AppShell>
  );
}
