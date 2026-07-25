import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";
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
export function ProviderCard({ provider }: { provider: ProviderStatus }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <div>
          <CardTitle>{provider.display_name}</CardTitle>
          {provider.is_simulated && <p className="text-xs text-muted-foreground">Simulated — not a real institution connection.</p>}
        </div>
        <StatusBadge descriptor={createStatusDescriptor({ ...statusDescriptor[provider.connection_status], icon: "link" })} />
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
          <Field label="Accounts available" value={String(provider.accounts_available)} />
          <Field label="Last synchronized" value={formatDateTime(provider.last_synced_at)} />
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
        <div className="border-t border-border pt-3">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Approval requirements</p>
          <p className="text-sm text-foreground">{provider.approval_requirements}</p>
        </div>
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
