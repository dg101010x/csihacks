import { ChevronDown } from "lucide-react";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor, cn } from "@relief/design-system";
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
 *
 * Simplified card design per Canon Law III (clarity first): logo + name (large) +
 * status + summary + meta line, with technical details hidden in expandable section.
 */
export function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-3">
        <div className="flex-1">
          <CardTitle className="text-lg">{provider.display_name}</CardTitle>
          <p className="mt-1 text-sm text-foreground">
            Relief can see your balance and transactions here.
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
            Demo account — shown for demonstration. Session-only data.
          </p>
        )}

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center justify-between text-sm font-medium text-foreground hover:text-primary transition-colors"
        >
          <span>Technical details</span>
          <ChevronDown className={cn("size-4 transition-transform", expanded && "rotate-180")} />
        </button>

        {expanded && (
          <div className="space-y-3 border-t border-border pt-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Accounts available</p>
              <p className="text-sm text-foreground">{provider.accounts_available}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Pending requests</p>
              <p className="text-sm text-foreground">{provider.pending_requests}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Expected response time</p>
              <p className="text-sm text-foreground">{provider.expected_response_time}</p>
            </div>
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
