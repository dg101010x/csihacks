import type { ForecastResponseV1 } from "@relief/contracts";
import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";

const rows: Array<{ key: keyof ForecastResponseV1["distress_probabilities"]; label: string }> = [
  { key: "essential_reserve_violation", label: "Essential reserve violation" },
  { key: "negative_balance", label: "Negative balance" },
  { key: "missed_obligation", label: "Missed obligation" },
];

/** Section 21.2. Verified/strongly projected risk only uses Risk Coral (Section 19, rule 6). */
export function RiskSummaryCard({ forecast }: { forecast: ForecastResponseV1 }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk summary</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ul className="flex flex-col gap-2">
          {rows.map(({ key, label }) => {
            const probability = forecast.distress_probabilities[key];
            const tone = probability >= 0.5 ? "risk" : probability >= 0.2 ? "caution" : "positive";
            return (
              <li key={key} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{label}</span>
                <StatusBadge
                  descriptor={createStatusDescriptor({
                    tone,
                    label: `${Math.round(probability * 100)}%`,
                    icon: "probability",
                  })}
                />
              </li>
            );
          })}
        </ul>

        {forecast.reason_factors.length > 0 && (
          <div className="flex flex-col gap-2 border-t border-border pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Why</p>
            {forecast.reason_factors.map((factor) => (
              <p key={factor.factor} className="text-sm text-foreground">
                {factor.description}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
