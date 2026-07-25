"use client";

import { StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { useForecastEnvelope } from "@/domain/hooks";

/** Section 5, item 6 — appears only while a Scenario Lab scenario is active. */
export function ScenarioBadge() {
  const { data } = useForecastEnvelope();
  if (!data?.envelope.scenario_active) return null;
  return (
    <StatusBadge descriptor={createStatusDescriptor({ tone: "caution", label: "Scenario active", icon: "flask-conical" })} />
  );
}
