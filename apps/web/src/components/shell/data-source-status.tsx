import { StatusBadge, createStatusDescriptor } from "@relief/design-system";

/**
 * Section 21.1 — surfaces which data source is active and how fresh it is.
 * Section 76: when a provider is unavailable, mark data as stale and show
 * the last successful synchronization time rather than hiding the problem.
 */
export function DataSourceStatus({
  source = "synthetic_wells_fargo",
  freshness = "current",
}: {
  source?: "synthetic_wells_fargo" | "plaid_sandbox";
  freshness?: "current" | "stale" | "unavailable";
}) {
  const sourceLabel = source === "plaid_sandbox" ? "Plaid Sandbox" : "Synthetic Wells Fargo";

  if (freshness === "current") {
    return (
      <StatusBadge
        descriptor={createStatusDescriptor({ tone: "positive", label: `${sourceLabel} — current`, icon: "check" })}
      />
    );
  }
  if (freshness === "stale") {
    return (
      <StatusBadge
        descriptor={createStatusDescriptor({ tone: "caution", label: `${sourceLabel} — stale`, icon: "clock" })}
      />
    );
  }
  return (
    <StatusBadge
      descriptor={createStatusDescriptor({ tone: "risk", label: `${sourceLabel} — unavailable`, icon: "alert" })}
    />
  );
}
