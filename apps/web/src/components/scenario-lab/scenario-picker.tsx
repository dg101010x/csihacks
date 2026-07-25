"use client";

import { useState } from "react";
import { Button, Card, CardContent, Input, StatusBadge, createStatusDescriptor, cn } from "@relief/design-system";
import { SCENARIO_PRESETS } from "@/domain/client";
import type { ScenarioDefinition } from "@/domain/types";

const MODELED_SCENARIO_ID = "scenario_paycheck_reduction";

/**
 * Section 8 — scenario presets, editable custom input. Only the paycheck
 * reduction preset has real simulation logic in this build's synthetic
 * adapter (see docs/ui_architecture.md); the rest are honestly labeled
 * rather than faked, per Section 3.10's "no fake integration ambiguity."
 */
export function ScenarioPicker({
  selected,
  onSelect,
  onApply,
  isApplying,
  isModeledScenarioActive,
}: {
  selected: ScenarioDefinition;
  onSelect: (scenario: ScenarioDefinition) => void;
  onApply: () => void;
  isApplying: boolean;
  isModeledScenarioActive: boolean;
}) {
  const [customLabel, setCustomLabel] = useState("Custom event");
  const [customAmount, setCustomAmount] = useState("");

  const isModeled = selected.id === MODELED_SCENARIO_ID;
  const isCustom = selected.id === "scenario_custom";

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {SCENARIO_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => onSelect(preset)}
              className={cn(
                "flex flex-col gap-1 rounded-md border p-3 text-left transition-colors duration-fast",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
                selected.id === preset.id ? "border-primary bg-accent" : "border-border hover:bg-accent/50",
              )}
            >
              <span className="text-sm font-medium text-foreground">{preset.label}</span>
              <span className="text-xs text-muted-foreground">{preset.description}</span>
              {preset.id !== MODELED_SCENARIO_ID && (
                <StatusBadge
                  descriptor={createStatusDescriptor({ tone: "neutral", label: "Not modeled in this build", icon: "info" })}
                  className="mt-1 w-fit"
                />
              )}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onSelect({ id: "scenario_custom", label: customLabel, kind: "custom", paycheck_delta_cents: 0, description: customLabel })}
            className={cn(
              "flex flex-col gap-2 rounded-md border p-3 text-left transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              isCustom ? "border-primary bg-accent" : "border-border hover:bg-accent/50",
            )}
          >
            <span className="text-sm font-medium text-foreground">Custom event</span>
            <Input
              value={customLabel}
              onChange={(e) => setCustomLabel(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              placeholder="Describe the event"
              className="h-8 text-xs"
            />
            <Input
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              placeholder="Amount, e.g. -150.00"
              className="h-8 text-xs"
            />
            <StatusBadge
              descriptor={createStatusDescriptor({ tone: "neutral", label: "Not modeled in this build", icon: "info" })}
              className="w-fit"
            />
          </button>
        </div>

        <div className="flex items-center justify-between border-t border-border pt-4">
          <div>
            <p className="text-sm font-medium text-foreground">{selected.label}</p>
            <p className="text-xs text-muted-foreground">{selected.description}</p>
          </div>
          <Button onClick={onApply} isLoading={isApplying} disabled={!isModeled || isModeledScenarioActive}>
            {isModeledScenarioActive && isModeled ? "Scenario applied" : "Apply scenario"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
