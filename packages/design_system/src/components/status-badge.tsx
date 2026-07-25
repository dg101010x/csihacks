import * as React from "react";
import { AlertOctagon, AlertTriangle, CheckCircle2, Circle } from "lucide-react";
import { cn } from "../cn";
import type { StatusDescriptor, StatusTone } from "../accessibility";

const toneStyles: Record<StatusTone, string> = {
  neutral: "bg-secondary text-secondary-foreground",
  positive: "bg-positive/15 text-positive",
  caution: "bg-caution/15 text-caution",
  risk: "bg-risk/15 text-risk",
};

const toneIcons: Record<StatusTone, React.ComponentType<{ className?: string }>> = {
  neutral: Circle,
  positive: CheckCircle2,
  caution: AlertTriangle,
  risk: AlertOctagon,
};

/**
 * Renders a StatusDescriptor as text + icon (Section 19, rules 7-8 — never
 * color alone). The icon is always derived from `descriptor.tone` (a fixed,
 * predictable icon per tone) rather than from the free-text `descriptor.icon`
 * field — that field exists to force every call site to name an icon at
 * construction time (see `createStatusDescriptor`), not to select one here.
 */
export function StatusBadge({ descriptor, className }: { descriptor: StatusDescriptor; className?: string }) {
  const Icon = toneIcons[descriptor.tone];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        toneStyles[descriptor.tone],
        className,
      )}
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {descriptor.label}
    </span>
  );
}
