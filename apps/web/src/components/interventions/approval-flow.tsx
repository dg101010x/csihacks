"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import { Button, Card, CardContent, CardHeader, CardTitle, Checkbox, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { useApproveIntervention, useApproveProviderCase } from "@/domain/hooks";
import { formatCents } from "@/lib/format";
import type { InterventionPackage, ProviderAction } from "@/domain/types";

type Stage = "review" | "submitted" | "pending_provider" | "executed";

/**
 * Section 9 — a staged action process: review, confirm permissions, submit
 * to provider, await provider response, accepted/rejected, executed.
 * Nothing is labeled "completed" before execution is actually confirmed.
 */
export function ApprovalFlow({ pkg, onClose }: { pkg: InterventionPackage; onClose: () => void }) {
  const [stage, setStage] = useState<Stage>("review");
  const [permissionsConfirmed, setPermissionsConfirmed] = useState(false);
  const [providerAction, setProviderAction] = useState<ProviderAction | null>(null);
  const approveIntervention = useApproveIntervention();
  const approveProviderCase = useApproveProviderCase();

  const requiresProvider = pkg.actions.some((a) => a.execution_mode === "provider_executable" || a.provider_capability_id);

  async function handleSubmit() {
    setStage("submitted");
    const action = await approveIntervention.mutateAsync(pkg.id);
    if (action && requiresProvider) {
      setProviderAction(action);
      setStage("pending_provider");
    } else {
      setStage("executed");
    }
  }

  async function handleProviderResponse() {
    if (providerAction) await approveProviderCase.mutateAsync(providerAction.id);
    setStage("executed");
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-deep-ink/40 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="flex-row items-start justify-between">
          <CardTitle>{pkg.label}</CardTitle>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close">
            <X className="size-4" aria-hidden="true" />
          </Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <ol className="flex flex-wrap gap-2 text-xs text-muted-foreground" aria-label="Approval progress">
            {(["review", "submitted", "pending_provider", "executed"] as const).map((s, i) => (
              <li key={s} className={`flex items-center gap-1 ${stageIndex(stage) >= i ? "text-foreground" : ""}`}>
                {stageIndex(stage) > i && <Check className="size-3 text-positive" aria-hidden="true" />}
                {stageLabel(s)}
                {i < 3 && <span aria-hidden="true">→</span>}
              </li>
            ))}
          </ol>

          {stage === "review" && (
            <>
              <p className="text-sm text-foreground">
                Added cost {formatCents(pkg.added_cost_cents)}. Required approvals: {pkg.required_approvals.join(", ")}.
              </p>
              <label className="flex items-start gap-2 text-sm text-foreground">
                <Checkbox checked={permissionsConfirmed} onChange={(e) => setPermissionsConfirmed(e.target.checked)} />
                I understand the actions in this package and confirm Relief may propose them.
              </label>
              <Button onClick={handleSubmit} disabled={!permissionsConfirmed}>
                Submit for approval
              </Button>
            </>
          )}

          {stage === "submitted" && <p className="text-sm text-muted-foreground">Submitting…</p>}

          {stage === "pending_provider" && providerAction && (
            <>
              <StatusBadge descriptor={createStatusDescriptor({ tone: "caution", label: "Awaiting provider response", icon: "clock" })} />
              <p className="text-sm text-foreground">{providerAction.consumer_impact_summary}</p>
              <p className="text-xs text-muted-foreground">{providerAction.provider_impact_summary}</p>
              <Button onClick={handleProviderResponse} isLoading={approveProviderCase.isPending}>
                Simulate provider response
              </Button>
            </>
          )}

          {stage === "executed" && (
            <>
              <StatusBadge descriptor={createStatusDescriptor({ tone: "positive", label: "Executed (simulated)", icon: "check" })} />
              <p className="text-sm text-foreground">
                This package has been executed in simulated mode — no real financial action was taken. See Audit for the full record.
              </p>
              <Button onClick={onClose}>Done</Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function stageIndex(stage: Stage): number {
  return ["review", "submitted", "pending_provider", "executed"].indexOf(stage);
}

function stageLabel(stage: Stage): string {
  return { review: "Review", submitted: "Submitted", pending_provider: "Provider review", executed: "Executed" }[stage];
}
