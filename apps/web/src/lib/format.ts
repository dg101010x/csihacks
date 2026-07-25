export function formatCents(cents: number): string {
  return (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD" });
}

/**
 * Date-only strings ("2026-07-31") are parsed by `new Date()` as UTC
 * midnight per ISO 8601 — displaying that in a negative-UTC-offset local
 * timezone rolls it back to the previous calendar day. Full datetime
 * strings ("...T09:00:00Z") don't have this problem. Parse date-only
 * strings from their Y/M/D components directly so they're never shifted.
 */
export function formatDate(iso: string): string {
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(iso);
  const date = dateOnly
    ? new Date(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)))
    : new Date(iso);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
