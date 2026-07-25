import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import type { RiskWindow } from "@/domain/types";

/** Section 7 — explicit list of detected collisions, alongside the chart's shaded regions. */
export function RiskWindowList({ windows }: { windows: RiskWindow[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Detected risk windows</CardTitle>
      </CardHeader>
      <CardContent>
        {windows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No reserve-violation risk detected in this forecast.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {windows.map((window) => (
              <li key={window.id} className="flex items-start gap-3 rounded-md border border-risk/30 bg-risk/5 p-3">
                <AlertTriangle className="mt-0.5 size-4 shrink-0 text-risk" aria-hidden="true" />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {formatDate(window.start_date)}
                    {window.end_date !== window.start_date && ` – ${formatDate(window.end_date)}`}
                  </p>
                  <p className="text-sm text-muted-foreground">{window.description}</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Lowest projected balance {formatCents(window.projected_lowest_balance_cents)} ·{" "}
                    {Math.round(window.probability * 100)}% probability · {Math.round(window.evidence.confidence * 100)}% confidence
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
