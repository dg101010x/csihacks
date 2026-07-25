"use client";

import { AppShell } from "@/components/shell/app-shell";
import { DataTrustCard } from "@/components/data/data-trust-card";
import { useDataTrust } from "@/domain/hooks";
import { LoadingState } from "@relief/design-system";

/** Data (Section 13) — source freshness, lineage, quality, and model inputs. */
export default function DataPage() {
  const trust = useDataTrust();

  if (trust.isLoading) {
    return (
      <AppShell title="Data">
        <LoadingState label="Loading data trust information…" />
      </AppShell>
    );
  }

  return (
    <AppShell title="Data">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(trust.data ?? []).map((source) => (
          <DataTrustCard key={source.source} trust={source} />
        ))}
      </div>
    </AppShell>
  );
}
