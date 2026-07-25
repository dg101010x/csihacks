import { PrimaryNavigation } from "./primary-navigation";
import { ContextHeader } from "./context-header";
import type { Environment } from "./environment-badge";

/** Section 21.1. */
export function AppShell({
  title,
  environment,
  children,
}: {
  title: string;
  environment?: Environment;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      <PrimaryNavigation />
      <div className="flex flex-1 flex-col">
        <ContextHeader title={title} environment={environment} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
