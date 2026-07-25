import { Button, Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { formatCents } from "@/lib/format";
import type { InterventionPackage } from "@/domain/types";

const effortLabel = { low: "Low effort", medium: "Medium effort", high: "High effort" } as const;
const reversibilityLabel = {
  fully_reversible: "Fully reversible",
  partially_reversible: "Partially reversible",
  irreversible: "Irreversible",
} as const;

/**
 * Section 9 — an intervention is a structured package with modeled
 * consequences, not a generic recommendation. All 13 required fields are
 * shown; nothing here is decorative (Section 3.7).
 */
export function InterventionCard({
  pkg,
  rank,
  onSelect,
  disabled,
}: {
  pkg: InterventionPackage;
  rank: number;
  onSelect: () => void;
  disabled?: boolean;
}) {
  const providerActions = pkg.actions.filter((a) => a.execution_mode === "provider_executable" || a.provider_capability_id);

  return (
    <Card className={rank === 0 ? "border-primary/40" : undefined}>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {rank === 0 ? "Recommended" : `Alternative ${rank}`}
          </p>
          <CardTitle>{pkg.label}</CardTitle>
        </div>
        <StatusBadge
          descriptor={createStatusDescriptor({
            tone: pkg.remaining_risk.essential_reserve_violation ? "caution" : "positive",
            label: pkg.remaining_risk.essential_reserve_violation ? "Residual risk remains" : "Clears reserve risk",
            icon: "shield",
          })}
        />
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <p className="text-sm text-foreground">{pkg.description}</p>

        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Obligations affected</p>
          <p className="text-sm text-foreground">{pkg.actions.map((a) => a.display_name).join("; ")}</p>
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
          <Field label="Added cost" value={formatCents(pkg.added_cost_cents)} />
          <Field label="New minimum balance" value={formatCents(pkg.new_minimum_balance_cents)} />
          <Field label="User effort" value={effortLabel[pkg.user_effort]} />
          <Field label="Provider modification" value={providerActions.length > 0 ? "Required" : "None"} />
          <Field
            label="Provider acceptance"
            value={pkg.provider_acceptance_probability != null ? `${Math.round(pkg.provider_acceptance_probability * 100)}%` : "Approval likelihood unavailable"}
          />
          <Field label="Model confidence" value={`${Math.round(pkg.evidence.confidence * 100)}%`} />
          <Field label="Reversibility" value={reversibilityLabel[pkg.reversibility]} />
          <Field label="Constitution" value={pkg.constitution_compatible ? "Compatible" : "Conflicts"} />
        </dl>

        <p className="border-t border-border pt-3 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Why this ranking: </span>
          {pkg.ranking_reason}
        </p>

        <Button size="sm" onClick={onSelect} disabled={disabled}>
          Review this package
        </Button>
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-foreground">{value}</dd>
    </div>
  );
}
