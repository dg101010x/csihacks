import { StatusBadge, createStatusDescriptor } from "@relief/design-system";

export type Environment = "simulated" | "sandbox" | "test" | "production";

const labels: Record<Environment, string> = {
  simulated: "Simulated",
  sandbox: "Sandbox",
  test: "Test",
  production: "Production",
};

/**
 * Section 21.1: must display Simulated / Sandbox / Test / Production. The
 * demonstration must always display "Simulated" — apps/web has no
 * production data source yet, so this is hardcoded rather than derived.
 */
export function EnvironmentBadge({ environment = "simulated" }: { environment?: Environment }) {
  return (
    <StatusBadge
      descriptor={createStatusDescriptor({
        tone: environment === "production" ? "positive" : "caution",
        label: labels[environment],
        icon: "flask",
      })}
    />
  );
}
