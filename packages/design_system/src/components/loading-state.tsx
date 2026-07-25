import * as React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../cn";

/**
 * A labeled spinner for whole-surface initial loading (Section 26, item 1).
 * The label is required — a spinner alone is not an accessible status
 * (Section 19, rule 8 applies to loading states too).
 */
export function LoadingState({ label, className }: { label: string; className?: string }) {
  return (
    <div role="status" className={cn("flex items-center gap-2 py-8 text-sm text-muted-foreground", className)}>
      <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
