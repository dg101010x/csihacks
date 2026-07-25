import type { ObligationV1 } from "@relief/contracts";
import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import { EssentialityIndicator } from "./essentiality-indicator";

/** Section 21.2 (card), backed by ObligationCard-level data (Section 21.4). */
export function UpcomingObligationsCard({ obligations }: { obligations: ObligationV1[] }) {
  const sorted = [...obligations].sort((a, b) => (a.next_due_at ?? "").localeCompare(b.next_due_at ?? ""));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upcoming obligations</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-3">
          {sorted.map((obligation) => (
            <li key={obligation.obligation_id} className="flex items-center justify-between gap-3">
              <div className="flex flex-col gap-1">
                <span className="text-sm font-medium text-foreground">{obligation.display_name}</span>
                <div className="flex items-center gap-2">
                  {obligation.next_due_at && (
                    <span className="text-xs text-muted-foreground">Due {formatDate(obligation.next_due_at)}</span>
                  )}
                  <EssentialityIndicator score={obligation.essentiality_score} />
                </div>
              </div>
              <span className="font-mono text-sm tabular-nums text-foreground">
                {formatCents(obligation.scheduled_amount_cents)}
              </span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
