"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { HouseholdSnapshotV1, ForecastResponseV1 } from "@relief/contracts";
import type { ResilienceScoreV1 } from "@relief/test-fixtures";
import { apiGet, apiPost } from "@/lib/api";

// Server state (Section 25.1): account data, forecast results, and
// resilience score all flow through TanStack Query.

export function useHouseholdSnapshot() {
  return useQuery({
    queryKey: ["household-snapshot"],
    queryFn: () => apiGet<HouseholdSnapshotV1>("/v1/households/current/snapshot"),
  });
}

export function useResilienceScore() {
  return useQuery({
    queryKey: ["resilience-score"],
    queryFn: () => apiGet<ResilienceScoreV1>("/v1/resilience/current"),
  });
}

export function useForecast() {
  return useQuery({
    queryKey: ["forecast"],
    queryFn: () => apiPost<ForecastResponseV1>("/v1/forecasts"),
  });
}

function useInvalidateHouseholdQueries() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ["household-snapshot"] }),
      queryClient.invalidateQueries({ queryKey: ["resilience-score"] }),
      queryClient.invalidateQueries({ queryKey: ["forecast"] }),
    ]);
}

/** The Section 16.3 shock simulator (/demo route) — demo-only, not a production action. */
export function useTriggerShock() {
  const invalidate = useInvalidateHouseholdQueries();
  return useMutation({
    mutationFn: () => apiPost<{ household_snapshot: HouseholdSnapshotV1; forecast: ForecastResponseV1 }>("/v1/demo/shock"),
    onSuccess: () => invalidate(),
  });
}

export function useResetDemo() {
  const invalidate = useInvalidateHouseholdQueries();
  return useMutation({
    mutationFn: () => apiPost<{ household_snapshot: HouseholdSnapshotV1 }>("/v1/demo/reset"),
    onSuccess: () => invalidate(),
  });
}
