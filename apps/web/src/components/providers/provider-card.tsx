"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  StatusBadge,
  cn,
  createStatusDescriptor,
} from "@relief/design-system";
import { formatDateTime } from "@/lib/format";
import type { ProviderStatus } from "@/domain/types";

const statusDescriptor = {
  connected: { tone: "positive" as const, label: "Connected" },
  degraded: { tone: "caution" as const, label: "Degraded" },
  disconnected: { tone: "risk" as const, label: "Disconnected" },
};

/**
 * Section 12 — provider operations. Wells Fargo (synthetic) is presented
 * as a reference institution, never implying an official partnership.
 */
export function ProviderCard({
  provider,
  onConnect,
  isConnecting = false,
}: {
  provider: ProviderStatus;
  onConnect?: () => void;
  isConnecting?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const detailsId = `provider-details-${provider.provider_id}`;

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div className="flex-1">
          <CardTitle className="text-lg">{provider.display_name}</CardTitle>
          <p className="mt-1 text-sm text-foreground">
            Relief can read balances and transactions from this source.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">
            Last checked {formatDateTime(provider.last_synced_at)}
          </p>
        </div>
        <StatusBadge descriptor={createStatusDescriptor({ ...statusDescriptor[provider.connection_status], icon: "link" })} />
      </CardHeader>

      <CardContent className="flex flex-col gap-3 border-t border-border pt-3">
        {provider.is_simulated && (
          <p className="text-xs text-muted-foreground">
            Demo account — simulated data only; no real financial action can occur.
          </p>
        )}

        {onConnect && provider.connection_status === "disconnected" && (
          <Button onClick={onConnect} isLoading={isConnecting}>
            Connect Plaid Sandbox
          </Button>
        )}

        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={detailsId}
          onClick={() => setExpanded((value) => !value)}
          className="flex min-h-11 items-center justify-between text-sm font-medium text-foreground transition-colors duration-fast hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          <span>Technical details</span>
          <ChevronDown className={cn("size-4 transition-transform duration-fast", expanded && "rotate-180")} aria-hidden="true" />
        </button>

        {expanded && (
          <div id={detailsId} className="space-y-4 border-t border-border pt-3">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
              <Field label="Accounts available" value={String(provider.accounts_available)} />
              <Field label="Pending requests" value={String(provider.pending_requests)} />
              <Field label="Expected response time" value={provider.expected_response_time} />
            </dl>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Supported actions</p>
              <p className="text-sm text-foreground">{provider.supported_actions.join(", ") || "None"}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Unsupported actions</p>
              <p className="text-sm text-foreground">{provider.unsupported_actions.join(", ") || "None documented"}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Approval requirements</p>
              <p className="text-sm text-foreground">{provider.approval_requirements}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium text-foreground">{value}</dd>
    </div>
  );
}
