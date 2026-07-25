import { Card, CardContent, CardHeader, CardTitle, StatusBadge, createStatusDescriptor } from "@relief/design-system";
import { formatDateTime } from "@/lib/format";
import type { DataTrust } from "@/domain/types";

/**
 * Section 13 — data and model trust, without overwhelming the consumer.
 * Every field here traces a forecasted event back to its source.
 */
export function DataTrustCard({ trust }: { trust: DataTrust }) {
  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between">
        <CardTitle>{trust.source.replaceAll("_", " ")}</CardTitle>
        <StatusBadge
          descriptor={createStatusDescriptor(
            trust.stale
              ? { tone: "caution", label: "Stale", icon: "clock" }
              : { tone: "positive", label: "Current", icon: "check" },
          )}
        />
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-3">
          <Field label="Last refresh" value={formatDateTime(trust.last_refresh_at)} />
          <Field label="Coverage period" value={`${trust.coverage_start} – ${trust.coverage_end}`} />
          <Field label="Duplicate events detected" value={String(trust.duplicate_events_detected)} />
          <Field label="Event classification confidence" value={`${Math.round(trust.event_classification_confidence * 100)}%`} />
          <Field label="Forecast provider" value={`${trust.forecast_provider} (${trust.forecast_provider_version})`} />
          <Field label="ReliefFM version" value={trust.relieffm_version ?? "Not connected"} />
        </dl>

        {trust.missing_data_notes.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Missing data</p>
            <ul className="mt-1 list-inside list-disc text-sm text-foreground">
              {trust.missing_data_notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {trust.calibration_summary && (
          <div className="border-t border-border pt-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Calibration</p>
            <p className="text-sm text-foreground">{trust.calibration_summary}</p>
          </div>
        )}

        {trust.known_limitations.length > 0 && (
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Known limitations</p>
            <ul className="mt-1 list-inside list-disc text-sm text-muted-foreground">
              {trust.known_limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
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
