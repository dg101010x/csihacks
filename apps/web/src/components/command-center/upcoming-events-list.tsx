import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import type { ForecastEnvelope } from "@/domain/types";

/** Section 6.5 — the next five meaningful financial events, chronologically. */
export function UpcomingEventsList({ envelope, confidenceById }: { envelope: ForecastEnvelope; confidenceById: Map<string, number> }) {
  const events = envelope.points
    .flatMap((point) => point.events.map((event) => ({ event, balanceAfter: point.median_balance_cents })))
    .slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upcoming events</CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">No known events in this window.</p>
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {events.map(({ event, balanceAfter }) => {
              const confidence = confidenceById.get(event.obligation_id ?? "") ?? 0.95;
              return (
                <li key={event.event_id} className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div>
                    <p className="text-sm font-medium text-foreground">{event.merchant_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatDate(event.effective_at)} · {event.merchant_category ?? event.event_type} ·{" "}
                      {Math.round(confidence * 100)}% confidence
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`font-mono text-sm tabular-nums ${event.direction === "inflow" ? "text-positive" : "text-foreground"}`}>
                      {event.direction === "inflow" ? "+" : "-"}
                      {formatCents(event.amount_cents)}
                    </p>
                    <p className="font-mono text-xs tabular-nums text-muted-foreground">→ {formatCents(balanceAfter)}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
