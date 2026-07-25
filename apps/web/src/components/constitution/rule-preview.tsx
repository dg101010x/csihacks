import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { formatCents } from "@/lib/format";
import type { ConstitutionRule, ConstitutionSimulationResult, InterventionPackage } from "@/domain/types";

/**
 * Section 10 — structured interpretation preview shown before activation:
 * trigger, scope, permitted/prohibited actions, approval requirement,
 * maximum monetary impact, expiration, priority, exceptions, confidence.
 */
export function RulePreview({
  rule,
  simulation,
  packages = [],
}: {
  rule: ConstitutionRule;
  simulation?: ConstitutionSimulationResult;
  packages?: InterventionPackage[];
}) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <CardTitle>Structured interpretation</CardTitle>
        <StatusBadge
          descriptor={createStatusDescriptor({
            tone: rule.confidence >= 0.8 ? "positive" : "caution",
            label: `${Math.round(rule.confidence * 100)}% confidence`,
            icon: "gauge",
          })}
        />
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <blockquote className="border-l-2 border-border pl-3 text-sm italic text-muted-foreground">
          &ldquo;{rule.raw_text}&rdquo;
        </blockquote>

        <dl className="grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2">
          <Field label="Trigger" value={rule.trigger} />
          <Field label="Scope" value={rule.scope.join(", ") || "—"} />
          <Field label="Permitted actions" value={rule.permitted_actions.join(", ") || "None specified"} />
          <Field label="Prohibited actions" value={rule.prohibited_actions.join(", ") || "None specified"} />
          <Field label="Approval requirement" value={rule.approval_requirement.replaceAll("_", " ")} />
          <Field
            label="Maximum monetary impact"
            value={rule.maximum_monetary_impact_cents != null ? formatCents(rule.maximum_monetary_impact_cents) : "Unlimited"}
          />
          <Field label="Expiration" value={rule.expiration ?? "None"} />
          <Field label="Priority" value={String(rule.priority)} />
          <Field label="Exceptions" value={rule.exceptions.join(", ") || "None"} />
        </dl>

        {simulation && (
          <div className="border-t border-border pt-4">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Tested against current interventions
            </p>
            <div className="mt-2 flex flex-col gap-1 text-sm">
              <p className="text-foreground">
                Allowed: {formatPackageList(simulation.allowed_package_ids, packages)}
              </p>
              <p className="text-foreground">
                Blocked: {formatPackageList(simulation.blocked_package_ids, packages)}
              </p>
            </div>
            {simulation.conflicts.length > 0 && (
              <ul className="mt-2 flex flex-col gap-1">
                {simulation.conflicts.map((c) => (
                  <li key={c.with_rule_id}>
                    <StatusBadge descriptor={createStatusDescriptor({ tone: "risk", label: c.description, icon: "alert" })} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatPackageList(ids: string[], packages: InterventionPackage[]): string {
  if (ids.length === 0) return "none";
  return ids.map((id) => packages.find((p) => p.id === id)?.label ?? id).join(", ");
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-foreground">{value}</dd>
    </div>
  );
}
