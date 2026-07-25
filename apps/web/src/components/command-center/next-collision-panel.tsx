"use client";

import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { buttonVariants, Card, CardContent } from "@relief/design-system";
import { formatCents, formatDate } from "@/lib/format";
import { useNow } from "@/hooks/use-now";
import type { RiskWindow } from "@/domain/types";
import type { Obligation } from "@/domain/types";

/** Section 6.3 — the next predicted issue, with links to act on it. */
export function NextCollisionPanel({ window, obligations }: { window: RiskWindow | null; obligations: Obligation[] }) {
  const now = useNow();

  if (!window) {
    return (
      <Card>
        <CardContent className="flex items-center gap-3 p-6">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-positive/15 text-positive">
            <AlertTriangle className="size-4" aria-hidden="true" />
          </div>
          <p className="text-sm text-foreground">No financial collision detected in the current forecast horizon.</p>
        </CardContent>
      </Card>
    );
  }

  const affected = window.causal_obligation_ids
    .map((id) => obligations.find((o) => o.obligation_id === id))
    .filter((o): o is Obligation => Boolean(o));
  const days = Math.max(0, Math.round((new Date(window.start_date).getTime() - now) / 86_400_000));

  return (
    <Card className="border-risk/30">
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="flex items-start gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-full bg-risk/15 text-risk">
            <AlertTriangle className="size-4" aria-hidden="true" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Next financial collision</p>
            <p className="text-sm text-muted-foreground">{window.description}</p>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Time until</dt>
            <dd className="text-sm font-medium text-foreground">{days === 0 ? "Today" : `${days} day${days === 1 ? "" : "s"}`}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Lowest balance</dt>
            <dd className="font-mono text-sm tabular-nums text-foreground">{formatCents(window.projected_lowest_balance_cents)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Probability</dt>
            <dd className="text-sm font-medium text-foreground">{Math.round(window.probability * 100)}%</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">Confidence</dt>
            <dd className="text-sm font-medium text-foreground">{Math.round(window.evidence.confidence * 100)}%</dd>
          </div>
        </dl>

        {affected.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Affected obligations:{" "}
            <span className="text-foreground">{affected.map((o) => o.display_name).join(", ")}</span> — due{" "}
            {formatDate(window.start_date)}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Link href="/timeline" className={buttonVariants({ size: "sm", variant: "secondary" })}>
            View detailed timeline
          </Link>
          <Link href="/scenario-lab" className={buttonVariants({ size: "sm", variant: "secondary" })}>
            Simulate a shock
          </Link>
          <Link href="/interventions" className={buttonVariants({ size: "sm" })}>
            View interventions
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}
