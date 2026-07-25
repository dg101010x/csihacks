"use client";

import { Card, CardContent } from "@relief/design-system";
import { formatDateTime } from "@/lib/format";
import type { AuditRecord } from "@/domain/types";

/** Section 11 — the ledger table. Selecting a row opens the evidence panel. */
export function AuditLedgerTable({ records, onSelect }: { records: AuditRecord[]; onSelect: (record: AuditRecord) => void }) {
  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th scope="col" className="px-4 py-3">Timestamp</th>
                <th scope="col" className="px-4 py-3">Event</th>
                <th scope="col" className="px-4 py-3">Actor</th>
                <th scope="col" className="px-4 py-3">Summary</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr
                  key={record.id}
                  onClick={() => onSelect(record)}
                  className="cursor-pointer border-b border-border transition-colors duration-fast last:border-0 hover:bg-accent"
                >
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-muted-foreground">
                    {formatDateTime(record.occurred_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 font-medium text-foreground">
                    {record.event_type.replaceAll("_", " ")}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-muted-foreground">{record.actor_type}</td>
                  <td className="px-4 py-3 text-foreground">{record.summary}</td>
                </tr>
              ))}
              {records.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    No audit records match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
