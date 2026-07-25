"use client";

import { useMemo, useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { AuditLedgerTable } from "@/components/audit/audit-ledger-table";
import { AuditDetailPanel } from "@/components/audit/audit-detail-panel";
import { useAuditRecords } from "@/domain/hooks";
import { LoadingState } from "@relief/design-system";
import type { AuditRecord } from "@/domain/types";

const ALL = "all";

/** Audit (Section 11) — the complete, filterable decision ledger. */
export default function AuditPage() {
  const audit = useAuditRecords();
  const [eventTypeFilter, setEventTypeFilter] = useState(ALL);
  const [actorFilter, setActorFilter] = useState(ALL);
  const [selected, setSelected] = useState<AuditRecord | null>(null);

  const records = useMemo(() => audit.data ?? [], [audit.data]);
  const eventTypes = useMemo(() => Array.from(new Set(records.map((r) => r.event_type))), [records]);
  const actorTypes = useMemo(() => Array.from(new Set(records.map((r) => r.actor_type))), [records]);

  const filtered = records.filter(
    (r) => (eventTypeFilter === ALL || r.event_type === eventTypeFilter) && (actorFilter === ALL || r.actor_type === actorFilter),
  );

  if (audit.isLoading) {
    return (
      <AppShell title="Audit">
        <LoadingState label="Loading the audit ledger…" />
      </AppShell>
    );
  }

  return (
    <AppShell title="Audit">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <FilterSelect label="Event type" value={eventTypeFilter} onChange={setEventTypeFilter} options={eventTypes} />
          <FilterSelect label="Actor" value={actorFilter} onChange={setActorFilter} options={actorTypes} />
          <p className="text-sm text-muted-foreground">{filtered.length} of {records.length} records</p>
        </div>

        <AuditLedgerTable records={filtered} onSelect={setSelected} />

        {selected && <AuditDetailPanel record={selected} onClose={() => setSelected(null)} />}
      </div>
    </AppShell>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-foreground">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <option value={ALL}>All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option.replaceAll("_", " ")}
          </option>
        ))}
      </select>
    </label>
  );
}
