"use client";

import { useState } from "react";
import Link from "next/link";
import { Inbox } from "lucide-react";
import { AppShell } from "@/components/shell/app-shell";
import { InterventionCard } from "@/components/interventions/intervention-card";
import { ComparisonTable } from "@/components/interventions/comparison-table";
import { ApprovalFlow } from "@/components/interventions/approval-flow";
import { useInterventionPackages, useRiskWindows } from "@/domain/hooks";
import { Button, EmptyState, LoadingState, buttonVariants } from "@relief/design-system";
import type { InterventionPackage } from "@/domain/types";

/** Section 9 — ranked protection strategies and the approval workflow. */
export default function InterventionsPage() {
  const interventions = useInterventionPackages();
  const riskWindows = useRiskWindows();
  const [showComparison, setShowComparison] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState<InterventionPackage | null>(null);

  if (interventions.isLoading || riskWindows.isLoading) {
    return (
      <AppShell title="Interventions">
        <LoadingState label="Loading interventions…" />
      </AppShell>
    );
  }

  const hasRisk = (riskWindows.data?.length ?? 0) > 0;
  const packages = interventions.data ?? [];

  return (
    <AppShell title="Interventions">
      {!hasRisk ? (
        <EmptyState
          icon={Inbox}
          title="No interventions needed right now"
          description="Sarah's forecast currently shows no reserve risk, so there's nothing to protect against. Try Scenario Lab to simulate a shock and see recommended interventions here."
          action={
            <Link href="/scenario-lab" className={buttonVariants({ size: "sm" })}>
              Open Scenario Lab
            </Link>
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{packages.length} ranked packages, safest and cheapest first.</p>
            <Button size="sm" variant="secondary" onClick={() => setShowComparison((v) => !v)}>
              {showComparison ? "Hide comparison" : "Compare top 3"}
            </Button>
          </div>

          {showComparison && <ComparisonTable packages={packages} />}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            {packages.map((pkg, i) => (
              <InterventionCard key={pkg.id} pkg={pkg} rank={i} onSelect={() => setSelectedPackage(pkg)} />
            ))}
          </div>
        </div>
      )}

      {selectedPackage && <ApprovalFlow pkg={selectedPackage} onClose={() => setSelectedPackage(null)} />}
    </AppShell>
  );
}
