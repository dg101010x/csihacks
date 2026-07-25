"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { NavRail } from "./nav-rail";
import { EnvironmentIndicator } from "./environment-indicator";
import { GlobalTimestamp } from "./global-timestamp";
import { ScenarioBadge } from "./scenario-badge";
import { CommandPalette } from "./command-palette";
import { NotificationCenter } from "./notification-center";
import { UserMenu } from "./user-menu";

/**
 * Section 5 — the global application shell. Dense enough to read as
 * infrastructure, not a floating-card dashboard; collapses the nav rail
 * into a drawer under 1024px (Section 18).
 */
export function AppShell({ title, children }: { title: string; children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <div className="hidden lg:flex">
        <NavRail />
      </div>

      {drawerOpen && (
        <div className="fixed inset-0 z-30 flex lg:hidden">
          <div className="absolute inset-0 bg-deep-ink/40" onClick={() => setDrawerOpen(false)} aria-hidden="true" />
          <div className="relative z-10">
            <NavRail onNavigate={() => setDrawerOpen(false)} />
          </div>
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setDrawerOpen(false)}
            className="absolute right-4 top-4 flex size-8 items-center justify-center rounded-md bg-surface text-foreground"
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      )}

      <div className="flex flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3 sm:px-6 sm:py-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              aria-label="Open navigation"
              onClick={() => setDrawerOpen(true)}
              className="flex size-8 items-center justify-center rounded-md text-foreground hover:bg-accent lg:hidden"
            >
              <Menu className="size-4" aria-hidden="true" />
            </button>
            <div className="flex flex-col gap-0.5">
              <h1 className="text-lg font-semibold text-foreground sm:text-xl">{title}</h1>
              <GlobalTimestamp />
            </div>
          </div>

          <div className="flex flex-1 items-center justify-end gap-2 sm:flex-initial">
            <div className="hidden md:block">
              <CommandPalette />
            </div>
            <ScenarioBadge />
            <div className="hidden sm:flex">
              <EnvironmentIndicator />
            </div>
            <NotificationCenter />
            <UserMenu />
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
