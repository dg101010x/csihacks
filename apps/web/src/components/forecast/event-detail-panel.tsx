"use client";

import { X } from "lucide-react";
import { Button, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import type { ForecastPoint } from "@/domain/types";

/**
 * Section 7 — selecting a timeline event opens a detail panel with source,
 * amount, date range, confidence, classification, related account, model
 * reasoning, and effect on liquidity. A responsive side panel (Section 18).
 */
export function EventDetailPanel({ point, onClose }: { point: ForecastPoint; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end lg:absolute lg:inset-auto lg:right-0 lg:top-0 lg:h-full">
      <div className="absolute inset-0 bg-deep-ink/40 lg:hidden" onClick={onClose} aria-hidden="true" />
      <aside
        aria-label={`Details for ${formatDate(point.date)}`}
        className="relative z-10 flex h-full w-full max-w-sm flex-col gap-4 overflow-y-auto border-l border-border bg-surface p-5 shadow-overlay"
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">{formatDate(point.date)}</p>
            <p className="font-mono text-2xl font-semibold tabular-nums text-foreground">
              {formatCents(point.median_balance_cents)}
            </p>
            <p className="text-xs text-muted-foreground">
              Range {formatCents(point.lower_balance_cents)} – {formatCents(point.upper_balance_cents)}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close details">
            <X className="size-4" aria-hidden="true" />
          </Button>
        </div>

        {point.is_risk && (
          <StatusBadge
            descriptor={createStatusDescriptor({
              tone: "risk",
              label: `${Math.round(point.reserve_violation_probability * 100)}% reserve violation probability`,
              icon: "alert",
            })}
          />
        )}

        <div className="flex flex-col gap-3">
          <h3 className="text-sm font-semibold text-foreground">Events this day</h3>
          {point.events.length === 0 ? (
            <p className="text-sm text-muted-foreground">No income or obligation events on this day.</p>
          ) : (
            point.events.map((event) => (
              <div key={event.event_id} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">{event.merchant_name}</p>
                  <span className={`font-mono text-sm tabular-nums ${event.direction === "inflow" ? "text-positive" : "text-foreground"}`}>
                    {event.direction === "inflow" ? "+" : "-"}
                    {formatCents(event.amount_cents)}
                  </span>
                </div>
                <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <dt>Classification</dt>
                  <dd className="text-foreground">{event.merchant_category ?? event.event_type}</dd>
                  <dt>Source</dt>
                  <dd className="text-foreground">{event.source}</dd>
                  <dt>Status</dt>
                  <dd className="text-foreground">{event.event_status}</dd>
                  <dt>Recurring</dt>
                  <dd className="text-foreground">{event.is_recurring ? "Yes" : "No"}</dd>
                  <dt>Related account</dt>
                  <dd className="text-foreground">{event.account_id}</dd>
                </dl>
              </div>
            ))
          )}
        </div>

        <div className="flex flex-col gap-1 border-t border-border pt-3 text-xs text-muted-foreground">
          <p>Effect on liquidity: median balance {formatCents(point.median_balance_cents)} after this day&apos;s events.</p>
          <p>Model reasoning: deterministic replay of known scheduled events against the current account balance.</p>
        </div>
      </aside>
    </div>
  );
}
