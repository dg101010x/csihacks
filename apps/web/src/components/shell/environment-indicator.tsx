"use client";

import { StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { useProviderStatus } from "@/domain/hooks";

/**
 * Persistent environment + system status (Section 5, items 3-4 of the
 * redesign brief). Always shows "Synthetic Wells Fargo" — there is no live
 * institution connected in this build — plus an aggregate system status
 * derived from every connected provider's actual state.
 */
export function EnvironmentIndicator() {
  const { data } = useProviderStatus();
  const providers = data ?? [];
  const primary = providers.find((p) => p.provider_id === "synthetic_wells_fargo");

  const anyDegraded = providers.some((p) => p.connection_status === "degraded");
  const anyDisconnected = providers.some(
    (p) => p.connection_status === "disconnected" && p.provider_id !== "plaid_sandbox",
  );

  const systemStatus = anyDisconnected ? "degraded" : anyDegraded ? "delayed" : "current";
  const statusDescriptor =
    systemStatus === "current"
      ? { tone: "positive" as const, label: "System current" }
      : systemStatus === "delayed"
        ? { tone: "caution" as const, label: "System delayed" }
        : { tone: "risk" as const, label: "System degraded" };

  return (
    <div className="flex items-center gap-2">
      <StatusBadge
        descriptor={createStatusDescriptor({ tone: "caution", label: primary?.display_name ?? "Synthetic Wells Fargo", icon: "flask" })}
      />
      <StatusBadge descriptor={createStatusDescriptor({ ...statusDescriptor, icon: "activity" })} />
    </div>
  );
}
