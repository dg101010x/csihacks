import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import type { ConstitutionRule } from "@/domain/types";

export function ActiveRulesList({ rules }: { rules: ConstitutionRule[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Active rules</CardTitle>
      </CardHeader>
      <CardContent>
        {rules.length === 0 ? (
          <p className="text-sm text-muted-foreground">No active rules yet.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {rules.map((rule) => (
              <li key={rule.rule_id} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm text-foreground">{rule.raw_text}</p>
                  <StatusBadge descriptor={createStatusDescriptor({ tone: "positive", label: "Active", icon: "check" })} />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Scope: {rule.scope.join(", ")} · Approval: {rule.approval_requirement.replaceAll("_", " ")}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
