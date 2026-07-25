"use client";

import { useForecastEnvelope } from "@/domain/hooks";
import { formatDateTime } from "@/lib/format";

/** Section 5, item 5 — a global forecast timestamp shared across the shell. */
export function GlobalTimestamp() {
  const { data } = useForecastEnvelope();
  if (!data) return null;
  return (
    <p className="font-mono text-xs text-muted-foreground">
      Forecast as of {formatDateTime(data.envelope.evidence.generated_at)}
    </p>
  );
}
