import { Card, CardContent, CardHeader, CardTitle } from "@relief/design-system";
import { formatCents } from "@/lib/format";
import type { InterventionPackage } from "@/domain/types";

/**
 * Section 9 — comparison mode for the top three packages. Answers the four
 * questions the brief specifies directly, rather than a single hidden score.
 */
export function ComparisonTable({ packages }: { packages: InterventionPackage[] }) {
  const top3 = packages.slice(0, 3);
  const safest = top3.reduce((best, p) => (!p.remaining_risk.essential_reserve_violation ? p : best), top3[0]!);
  const cheapest = top3.reduce((best, p) => (p.added_cost_cents < best.added_cost_cents ? p : best), top3[0]!);
  const leastProviderMod = top3.reduce(
    (best, p) => (countProviderActions(p) < countProviderActions(best) ? p : best),
    top3[0]!,
  );
  const mostConstitutional = top3.find((p) => p.constitution_compatible) ?? top3[0]!;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comparing the top 3</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                <th scope="col" className="px-3 py-2">Question</th>
                <th scope="col" className="px-3 py-2">Answer</th>
              </tr>
            </thead>
            <tbody>
              <Row question="Which package creates the safest result?" answer={safest.label} />
              <Row question="Which package costs the least?" answer={`${cheapest.label} (${formatCents(cheapest.added_cost_cents)})`} />
              <Row question="Which package requires the least provider modification?" answer={leastProviderMod.label} />
              <Row question="Which package best follows Sarah's constitution?" answer={mostConstitutional.label} />
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function countProviderActions(pkg: InterventionPackage): number {
  return pkg.actions.filter((a) => a.execution_mode === "provider_executable" || a.provider_capability_id).length;
}

function Row({ question, answer }: { question: string; answer: string }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="px-3 py-3 text-muted-foreground">{question}</td>
      <td className="px-3 py-3 font-medium text-foreground">{answer}</td>
    </tr>
  );
}
