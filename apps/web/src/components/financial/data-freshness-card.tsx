import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { formatDateTime } from "@/lib/format";

/** Section 21.2 / Section 26 — stale data must display a visible warning. */
export function DataFreshnessCard({ generatedAt, isStale }: { generatedAt: string; isStale: boolean }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Data freshness</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Forecast generated {formatDateTime(generatedAt)}</p>
        <StatusBadge
          descriptor={createStatusDescriptor(
            isStale
              ? { tone: "caution", label: "Stale — revalidating", icon: "clock" }
              : { tone: "positive", label: "Current", icon: "check" },
          )}
        />
      </CardContent>
    </Card>
  );
}
