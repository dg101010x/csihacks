import { StatusBadge, createStatusDescriptor } from "@relief/design-system";

/**
 * Section 21.4. Essentiality is not itself a risk signal (Section 19, rule 6
 * reserves Risk Coral for verified/strongly projected risk) — always
 * neutral tone, the label carries the meaning.
 */
export function EssentialityIndicator({ score }: { score: number }) {
  const label = score >= 0.8 ? "Essential" : score >= 0.4 ? "Important" : "Flexible";
  return (
    <StatusBadge
      descriptor={createStatusDescriptor({ tone: "neutral", label: `${label} · ${Math.round(score * 100)}%`, icon: "gauge" })}
    />
  );
}
