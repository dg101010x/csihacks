"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ClipboardList,
  FlaskConical,
  Landmark,
  LayoutGrid,
  ScrollText,
  Scale,
  Database,
} from "lucide-react";
import { cn } from "@relief/design-system";

const links = [
  { href: "/", label: "Command Center", icon: LayoutGrid },
  { href: "/timeline", label: "Timeline", icon: Activity },
  { href: "/scenario-lab", label: "Scenario Lab", icon: FlaskConical },
  { href: "/interventions", label: "Interventions", icon: ClipboardList },
  { href: "/constitution", label: "Constitution", icon: Scale },
  { href: "/audit", label: "Audit", icon: ScrollText },
  { href: "/providers", label: "Providers", icon: Landmark },
  { href: "/data", label: "Data", icon: Database },
];

/** Section 4-5 of the redesign brief — the 8-item IA, compact nav rail. */
export function NavRail({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex h-full w-56 shrink-0 flex-col gap-1 bg-sidebar p-4 text-sidebar-foreground">
      <Link href="/" className="mb-6 px-2 text-lg font-semibold text-sidebar-foreground" onClick={onNavigate}>
        Relief
      </Link>
      {links.map((link) => {
        const active = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
        const Icon = link.icon;
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            onClick={onNavigate}
            className={cn(
              "flex min-h-11 items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
