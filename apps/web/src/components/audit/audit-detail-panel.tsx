"use client";

import { X } from "lucide-react";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatDateTime } from "@/lib/format";
import type { AuditRecord } from "@/domain/types";

/** Section 11 — the evidence panel opened by selecting an audit record. */
export function AuditDetailPanel({ record, onClose }: { record: AuditRecord; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-deep-ink/40 p-4">
      <Card className="w-full max-w-lg max-h-[85vh] overflow-y-auto">
        <CardHeader className="flex-row items-start justify-between">
          <CardTitle>{humanize(record.event_type)}</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <X className="size-4" aria-hidden="true" />
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm text-foreground">{record.summary}</p>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
            <Field label="Timestamp" value={formatDateTime(record.occurred_at)} />
            <Field label="Actor" value={`${record.actor_type} · ${record.actor_id}`} />
            <Field label="Request ID" value={record.request_id} mono />
            <Field label="Related model version" value={record.related_model_version ?? "—"} mono />
            <Field label="Before state" value={record.before_state ?? "—"} mono />
            <Field label="After state" value={record.after_state ?? "—"} mono />
            <Field label="Related constitution rule" value={record.related_constitution_rule_id ?? "—"} mono />
            <Field label="Data sources" value={record.related_data_sources.join(", ") || "—"} />
          </dl>

          <div className="border-t border-border pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Reason</p>
            <p className="mt-1 text-sm text-foreground">{record.reason}</p>
          </div>

          {record.evidence.length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Evidence</p>
              <ul className="mt-1 flex flex-col gap-1">
                {record.evidence.map((e) => (
                  <li key={e} className="font-mono text-xs text-foreground">
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function humanize(key: string): string {
  return key.replaceAll("_", " ");
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className={`text-sm text-foreground ${mono ? "font-mono text-xs" : "font-medium"}`}>{value}</dd>
    </div>
  );
}
