import { ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatCents } from "@/lib/format";
import type { ConstitutionRule } from "@/domain/types";

/** Section 6.4 — protections already in effect, derived from active constitution rules. */
export function ActiveProtections({ reserveCents, activeRules }: { reserveCents: number; activeRules: ConstitutionRule[] }) {
  const items: string[] = [`Essential reserve floor enabled: ${formatCents(reserveCents)}`];

  for (const rule of activeRules) {
    if (rule.scope.includes("housing")) {
      items.push("Rent modification requires your explicit approval before it's proposed to a provider.");
    }
    if (rule.scope.includes("subscriptions") && rule.approval_requirement === "always_ask") {
      items.push("Relief will always ask before pausing a subscription.");
    }
    if (rule.prohibited_actions.includes("term_extension_with_interest")) {
      items.push("Loan term extensions that add interest are never proposed.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Active protections</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-foreground">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-positive" aria-hidden="true" />
              {item}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
