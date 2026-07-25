import type { FinancialEventV1 } from "@relief/contracts";
import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";

/** Section 21.2. */
export function IncomeForecastCard({ knownFutureEvents }: { knownFutureEvents: FinancialEventV1[] }) {
  const nextIncome = knownFutureEvents
    .filter((event) => event.direction === "inflow")
    .sort((a, b) => a.effective_at.localeCompare(b.effective_at))[0];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Next income</CardTitle>
      </CardHeader>
      <CardContent>
        {nextIncome ? (
          <div className="flex items-baseline justify-between">
            <div>
              <p className="text-sm text-foreground">{nextIncome.merchant_name}</p>
              <p className="text-xs text-muted-foreground">{formatDate(nextIncome.effective_at)}</p>
            </div>
            <span className="font-mono text-lg font-semibold tabular-nums text-positive">
              {formatCents(nextIncome.amount_cents)}
            </span>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No known future income events.</p>
        )}
      </CardContent>
    </Card>
  );
}
