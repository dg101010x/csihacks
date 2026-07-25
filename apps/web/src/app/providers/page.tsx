"use client";

import { AppShell } from "@/components/shell/app-shell";
import { ProviderCard } from "@/components/providers/provider-card";
import { useProviderStatus, useAuditRecords, useConnectPlaidSandbox } from "@/domain/hooks";
import { Card, CardContent, CardHeader, CardTitle, LoadingState } from "@relief/design-system";
import { formatDateTime } from "@/lib/format";

/** Providers (Section 12) — connected institutions, capabilities, and provider responses. */
export default function ProvidersPage() {
  const providers = useProviderStatus();
  const audit = useAuditRecords();
  const connectPlaid = useConnectPlaidSandbox();

  if (providers.isLoading) {
    return (
      <AppShell title="Providers">
        <LoadingState label="Loading provider connections…" />
      </AppShell>
    );
  }

  const providerActivity = (audit.data ?? []).filter((r) => r.actor_type === "provider" || r.event_type.includes("provider"));

  return (
    <AppShell title="Providers">
      <div className="flex flex-col gap-4">
        {connectPlaid.isError && (
          <div role="alert" className="rounded-md border border-risk/40 bg-risk/5 p-3 text-sm text-risk">
            <p className="font-medium">Plaid Sandbox could not connect</p>
            <p>Check the local Plaid credentials and try again. The Sarah demo remains fully available.</p>
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {(providers.data ?? []).map((provider) => (
            <ProviderCard
              key={provider.provider_id}
              provider={provider}
              onConnect={provider.provider_id === "plaid_sandbox" ? () => connectPlaid.mutate() : undefined}
              isConnecting={connectPlaid.isPending}
            />
          ))}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Provider response history</CardTitle>
          </CardHeader>
          <CardContent>
            {providerActivity.length === 0 ? (
              <p className="text-sm text-muted-foreground">No provider responses yet.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {providerActivity.map((record) => (
                  <li key={record.id} className="flex items-center justify-between text-sm">
                    <span className="text-foreground">{record.summary}</span>
                    <span className="font-mono text-xs text-muted-foreground">{formatDateTime(record.occurred_at)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
