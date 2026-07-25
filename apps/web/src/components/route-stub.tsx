/**
 * Placeholder for routes not yet built out (Section 17). Each of these gets
 * replaced by real UI as Phase B-E land — tracked per-route below so it's
 * obvious what still needs building.
 */
export function RouteStub({
  title,
  description,
  phase,
}: {
  title: string;
  description: string;
  phase: string;
}) {
  return (
    <main className="flex min-h-screen flex-col items-start gap-3 px-8 py-16">
      <p className="font-mono text-xs uppercase tracking-wide text-muted">{phase}</p>
      <h1 className="text-2xl font-semibold text-foreground">{title}</h1>
      <p className="max-w-xl text-muted">{description}</p>
    </main>
  );
}
