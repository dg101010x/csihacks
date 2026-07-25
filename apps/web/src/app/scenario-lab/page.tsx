"use client";

import { useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell/app-shell";
import { ScenarioPicker } from "@/components/scenario-lab/scenario-picker";
import { ScenarioComparison } from "@/components/scenario-lab/scenario-comparison";
import { useApplyScenario, useResetScenario, useForecastEnvelope, useInterventionPackages } from "@/domain/hooks";
import { SCENARIO_PRESETS } from "@/domain/client";
import { Button, Card, CardContent, CardHeader, CardTitle, buttonVariants } from "@relief/design-system";
import { formatCents } from "@/lib/format";
import type { ScenarioDefinition, ScenarioResult } from "@/domain/types";

/**
 * Scenario Lab (Section 8) — replaces the old single-button shock
 * simulator. Baseline is never modified until the user explicitly applies
 * a scenario (Section 8, last line).
 */
export default function ScenarioLabPage() {
  const [selected, setSelected] = useState<ScenarioDefinition>(SCENARIO_PRESETS[0]!);
  const [savedScenarios, setSavedScenarios] = useState<ScenarioResult[]>([]);
  const forecast = useForecastEnvelope();
  const interventions = useInterventionPackages();
  const applyScenario = useApplyScenario();
  const resetScenario = useResetScenario();

  const isModeledScenarioActive = forecast.data?.envelope.scenario_active ?? false;

  return (
    <AppShell title="Scenario Lab">
      <div className="flex flex-col gap-4">
        <ScenarioPicker
          selected={selected}
          onSelect={setSelected}
          onApply={() => applyScenario.mutate(selected)}
          isApplying={applyScenario.isPending}
          isModeledScenarioActive={isModeledScenarioActive}
        />

        {isModeledScenarioActive && (
          <div className="flex items-center justify-between rounded-md border border-caution/40 bg-caution/10 px-4 py-3">
            <p className="text-sm text-foreground">A scenario is currently applied to the live forecast.</p>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => resetScenario.mutate(undefined, { onSuccess: () => applyScenario.reset() })}
              disabled={resetScenario.isPending}
            >
              Reset to baseline
            </Button>
          </div>
        )}

        {applyScenario.data && (
          <>
            <ScenarioComparison result={applyScenario.data} />

            <div className="flex items-center justify-between">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setSavedScenarios((prev) => [...prev, applyScenario.data!])}
              >
                Save this scenario
              </Button>
              <Link href="/interventions" className={buttonVariants({ size: "sm" })}>
                View recommended interventions
              </Link>
            </div>
          </>
        )}

        {interventions.data && interventions.data.length > 0 && isModeledScenarioActive && (
          <Card>
            <CardHeader>
              <CardTitle>Recommended interventions</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2">
                {interventions.data.slice(0, 3).map((pkg) => (
                  <li key={pkg.id} className="flex items-center justify-between text-sm">
                    <span className="text-foreground">{pkg.label}</span>
                    <span className="font-mono tabular-nums text-muted-foreground">
                      {formatCents(pkg.added_cost_cents)} added cost
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {savedScenarios.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Saved scenarios (this session)</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="flex flex-col gap-2">
                {savedScenarios.map((saved, i) => (
                  <li key={i} className="flex items-center justify-between text-sm">
                    <span className="text-foreground">{saved.scenario.label}</span>
                    <span className="font-mono tabular-nums text-muted-foreground">
                      Lowest balance {formatCents(saved.deltas.lowest_balance_delta_cents)}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
