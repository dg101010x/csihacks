import { EnvironmentBadge, type Environment } from "./environment-badge";
import { DataSourceStatus } from "./data-source-status";
import { UserMenu } from "./user-menu";

/** Section 21.1. */
export function ContextHeader({
  title,
  environment = "simulated",
}: {
  title: string;
  environment?: Environment;
}) {
  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-4">
      <h1 className="text-xl font-semibold text-foreground">{title}</h1>
      <div className="flex items-center gap-3">
        <DataSourceStatus />
        <EnvironmentBadge environment={environment} />
        <UserMenu />
      </div>
    </header>
  );
}
