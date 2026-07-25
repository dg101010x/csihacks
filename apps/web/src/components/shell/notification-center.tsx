"use client";

import { useState } from "react";
import Link from "next/link";
import { Bell, X } from "lucide-react";
import { cn } from "@relief/design-system";
import { useRiskWindows, useInterventionPackages } from "@/domain/hooks";
import { useClickOutside } from "@/hooks/use-click-outside";
import { formatDate } from "@/lib/format";

/** Section 5, item 8 — risk and intervention notifications, dismissible per session. */
export function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const riskWindows = useRiskWindows();
  const interventions = useInterventionPackages();
  const ref = useClickOutside<HTMLDivElement>(() => setOpen(false), open);

  const items = [
    ...(riskWindows.data ?? []).map((w) => ({
      id: w.id,
      tone: "risk" as const,
      title: `Reserve risk begins ${formatDate(w.start_date)}`,
      description: w.description,
      href: "/timeline",
    })),
    // Only surfaced when there's an actual risk to respond to — otherwise
    // this would decoratively suggest interventions nothing needs (Section
    // 3.7 of the redesign brief: no decorative data).
    ...((riskWindows.data?.length ?? 0) > 0 && interventions.data && interventions.data.length > 0
      ? [
          {
            id: "interventions_available",
            tone: "caution" as const,
            title: `${interventions.data.length} intervention${interventions.data.length === 1 ? "" : "s"} available`,
            description: interventions.data[0]!.ranking_reason,
            href: "/interventions",
          },
        ]
      : []),
  ].filter((item) => !dismissed.has(item.id));

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label={`Notifications${items.length > 0 ? ` (${items.length} unread)` : ""}`}
        className="relative flex size-8 items-center justify-center rounded-md text-foreground transition-colors duration-fast hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <Bell className="size-4" aria-hidden="true" />
        {items.length > 0 && (
          <span className="absolute right-1 top-1 flex size-2 rounded-full bg-risk" aria-hidden="true" />
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-20 mt-2 w-80 rounded-md border border-border bg-surface p-2 shadow-lg">
          {items.length === 0 ? (
            <p className="px-2 py-4 text-center text-sm text-muted-foreground">Nothing needs your attention.</p>
          ) : (
            <ul className="flex flex-col gap-1">
              {items.map((item) => (
                <li key={item.id} className={cn("flex items-start gap-2 rounded-sm p-2 hover:bg-accent")}>
                  <Link href={item.href} className="flex-1 text-sm" onClick={() => setOpen(false)}>
                    <p className="font-medium text-foreground">{item.title}</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">{item.description}</p>
                  </Link>
                  <button
                    type="button"
                    aria-label="Dismiss"
                    onClick={() => setDismissed((prev) => new Set(prev).add(item.id))}
                    className="shrink-0 rounded-sm p-1 text-muted-foreground hover:bg-border/60"
                  >
                    <X className="size-3.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
