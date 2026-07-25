import type { ResilienceScoreV1 } from "@relief/test-fixtures";
import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";

const trendDescriptor = {
  improving: { tone: "positive" as const, label: "Improving" },
  stable: { tone: "neutral" as const, label: "Stable" },
  declining: { tone: "risk" as const, label: "Declining" },
};

/**
 * Section 22 — Financial Resilience Score interface. The user must be able
 * to open the score and inspect every component (native <details>, so this
 * is keyboard operable and screen-reader friendly for free).
 */
export function ResilienceScoreCard({ score }: { score: ResilienceScoreV1 }) {
  const trend = trendDescriptor[score.trend];

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle>Financial Resilience Score</CardTitle>
        </div>
        <StatusBadge descriptor={createStatusDescriptor({ ...trend, icon: "trend" })} />
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-4xl font-semibold tabular-nums text-foreground">{score.overall}</span>
          <span className="text-sm text-muted-foreground">/ 100 · {Math.round(score.confidence * 100)}% confidence</span>
        </div>

        {score.primary_weakness && (
          <p className="text-sm text-muted-foreground">
            Primary weakness: <span className="text-foreground">{humanize(score.primary_weakness)}</span>
          </p>
        )}
        {score.primary_stabilizing_factor && (
          <p className="text-sm text-muted-foreground">
            Stabilizing factor: <span className="text-foreground">{humanize(score.primary_stabilizing_factor)}</span>
          </p>
        )}

        <details className="rounded-md border border-border">
          <summary className="cursor-pointer select-none px-3 py-2 text-sm font-medium text-foreground">
            Component breakdown
          </summary>
          <ul className="flex flex-col gap-2 border-t border-border px-3 py-2">
            {score.components.map((component) => (
              <li key={component.key} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  {component.label} <span className="text-xs">({Math.round(component.weight * 100)}%)</span>
                </span>
                <span className="font-mono tabular-nums text-foreground">{component.score}</span>
              </li>
            ))}
          </ul>
        </details>

        <p className="text-xs text-muted-foreground">{score.disclosure}</p>
      </CardContent>
    </Card>
  );
}

function humanize(key: string): string {
  return key.replaceAll("_", " ");
}
