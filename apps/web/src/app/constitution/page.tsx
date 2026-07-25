"use client";

import { useState } from "react";
import { AppShell } from "@/components/shell/app-shell";
import { ActiveRulesList } from "@/components/constitution/active-rules-list";
import { RulePreview } from "@/components/constitution/rule-preview";
import { useConstitutionRules, useInterventionPackages } from "@/domain/hooks";
import { reliefClient } from "@/domain/client";
import { Button, Card, CardContent, CardHeader, CardTitle, Checkbox, FormField, Textarea, LoadingState } from "@relief/design-system";
import type { ConstitutionRule, ConstitutionSimulationResult } from "@/domain/types";

/**
 * Constitution (Section 10) — a real consumer policy interface. Free-text
 * rules are parsed into a structured preview, tested against the active
 * forecast's interventions, checked for conflicts, and require explicit
 * confirmation before activation. Nothing here auto-activates.
 */
export default function ConstitutionPage() {
  const rules = useConstitutionRules();
  const interventions = useInterventionPackages();
  const [draftText, setDraftText] = useState("");
  const [draftRule, setDraftRule] = useState<ConstitutionRule | null>(null);
  const [simulation, setSimulation] = useState<ConstitutionSimulationResult | null>(null);
  const [locallyActivated, setLocallyActivated] = useState<ConstitutionRule[]>([]);
  const [confirmed, setConfirmed] = useState(false);

  if (rules.isLoading) {
    return (
      <AppShell title="Constitution">
        <LoadingState label="Loading your constitution…" />
      </AppShell>
    );
  }

  const activeRules = [...(rules.data?.active ?? []), ...locallyActivated];

  function parseDraft(text: string) {
    setDraftText(text);
    if (text.trim().length < 10) {
      setDraftRule(null);
      setSimulation(null);
      return;
    }
    const parsed = reliefClient.parseConstitutionRule(text);
    setDraftRule(parsed);
    setSimulation(reliefClient.simulateConstitutionRule(parsed, interventions.data ?? [], activeRules));
    setConfirmed(false);
  }

  function activate() {
    if (!draftRule) return;
    setLocallyActivated((prev) => [...prev, { ...draftRule, status: "active" }]);
    setDraftText("");
    setDraftRule(null);
    setSimulation(null);
    setConfirmed(false);
  }

  return (
    <AppShell title="Constitution">
      <div className="flex flex-col gap-4">
        <ActiveRulesList rules={activeRules} />

        <Card>
          <CardHeader>
            <CardTitle>Write a new rule</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <FormField
              id="rule-text"
              label="Describe the rule in your own words"
              hint="Example: Never delay rent without asking me first. You may pause subscriptions under $25.00 when my essential reserve is at risk."
            >
              <Textarea
                id="rule-text"
                rows={3}
                value={draftText}
                onChange={(e) => parseDraft(e.target.value)}
                placeholder="Never delay rent without asking me first…"
              />
            </FormField>

            {rules.data && rules.data.starters.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-xs text-muted-foreground">Starter rules:</span>
                {rules.data.starters.map((starter) => (
                  <button
                    key={starter.rule_id}
                    type="button"
                    onClick={() => parseDraft(starter.raw_text)}
                    className="text-xs text-primary underline underline-offset-2"
                  >
                    {starter.raw_text.slice(0, 40)}…
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {draftRule && (
          <>
            <RulePreview rule={draftRule} simulation={simulation ?? undefined} packages={interventions.data ?? []} />
            <Card>
              <CardContent className="flex items-center justify-between p-6">
                <label className="flex items-center gap-2 text-sm text-foreground">
                  <Checkbox checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
                  I&apos;ve reviewed this interpretation and want to activate it.
                </label>
                <Button onClick={activate} disabled={!confirmed}>
                  Activate rule
                </Button>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
