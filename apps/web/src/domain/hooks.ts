"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { reliefClient } from "./client";
import type { ScenarioDefinition } from "./types";

/**
 * Every hook here is keyed under the shared ["relief", ...] namespace so a
 * single `invalidateQueries({ queryKey: ["relief"] })` (no `exact`) after a
 * scenario change refreshes every dependent screen at once — Command
 * Center, Timeline, Interventions, and Scenario Lab all read the same
 * underlying forecast state.
 */
const keys = {
  root: ["relief"] as const,
  forecast: () => [...keys.root, "forecast"] as const,
  interventions: () => [...keys.root, "interventions"] as const,
  constitution: () => [...keys.root, "constitution"] as const,
  audit: () => [...keys.root, "audit"] as const,
  providers: () => [...keys.root, "providers"] as const,
  data: () => [...keys.root, "data"] as const,
};

export function useForecastEnvelope() {
  return useQuery({
    queryKey: keys.forecast(),
    queryFn: () => reliefClient.getForecastEnvelope(),
  });
}

export function useInterventionPackages() {
  return useQuery({
    queryKey: keys.interventions(),
    queryFn: () => reliefClient.getInterventionPackages(),
  });
}

export function useConstitutionRules() {
  return useQuery({
    queryKey: keys.constitution(),
    queryFn: () => reliefClient.getConstitutionRules(),
  });
}

export function useAuditRecords() {
  return useQuery({
    queryKey: keys.audit(),
    queryFn: () => reliefClient.getAuditRecords(),
  });
}

export function useProviderStatus() {
  return useQuery({
    queryKey: keys.providers(),
    queryFn: () => reliefClient.getProviderStatus(),
  });
}

export function useDataTrust() {
  return useQuery({
    queryKey: keys.data(),
    queryFn: () => reliefClient.getDataTrust(),
  });
}

function useInvalidateAll() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: keys.root });
}

export function useApplyScenario() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (scenario: ScenarioDefinition) => reliefClient.applyScenario(scenario),
    onSuccess: () => invalidateAll(),
  });
}

export function useResetScenario() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: () => reliefClient.resetScenario(),
    onSuccess: () => invalidateAll(),
  });
}

export function useApproveIntervention() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (packageId: string) => reliefClient.approveIntervention(packageId),
    onSuccess: () => invalidateAll(),
  });
}

export function useApproveProviderCase() {
  const invalidateAll = useInvalidateAll();
  return useMutation({
    mutationFn: (caseId: string) => reliefClient.approveProviderCase(caseId),
    onSuccess: () => invalidateAll(),
  });
}
