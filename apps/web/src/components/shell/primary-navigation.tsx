"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@relief/design-system";

const links = [
  { href: "/demo", label: "Demo" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/timeline", label: "Timeline" },
  { href: "/interventions", label: "Interventions" },
  { href: "/constitution", label: "Constitution" },
  { href: "/audit", label: "Audit" },
  { href: "/provider", label: "Provider" },
];

/** Section 21.1. Deep Ink surface per Section 19 rule 1 (navigation). */
export function PrimaryNavigation() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex h-full w-56 shrink-0 flex-col gap-1 bg-sidebar p-4 text-sidebar-foreground">
      <Link href="/" className="mb-6 px-2 text-lg font-semibold text-sidebar-foreground">
        Relief
      </Link>
      {links.map((link) => {
        const active = pathname === link.href || pathname.startsWith(`${link.href}/`);
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors duration-fast",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring",
              active
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
