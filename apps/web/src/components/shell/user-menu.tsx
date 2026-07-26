"use client";

import { useState } from "react";
import { ChevronDown, RotateCcw } from "lucide-react";
import { useResetScenario } from "@/domain/hooks";
import { useClickOutside } from "@/hooks/use-click-outside";

/** Section 5, item 9 — user menu with a real demo-reset action. */
export function UserMenu({ name = "Sarah" }: { name?: string }) {
  const [open, setOpen] = useState(false);
  const reset = useResetScenario();
  const ref = useClickOutside<HTMLDivElement>(() => setOpen(false), open);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex min-h-11 items-center gap-2 rounded-md px-2 text-sm text-foreground transition-colors duration-fast hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span
          aria-hidden="true"
          className="flex size-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground"
        >
          {name.charAt(0)}
        </span>
        <span className="hidden sm:inline">{name}</span>
        <ChevronDown className="hidden size-3.5 text-muted-foreground sm:block" aria-hidden="true" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full z-20 mt-2 w-56 rounded-md border border-border bg-surface p-1 shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              reset.mutate();
              setOpen(false);
            }}
            className="flex min-h-11 w-full items-center gap-2 rounded-sm px-2 py-2 text-left text-sm text-foreground transition-colors duration-fast hover:bg-accent"
          >
            <RotateCcw className="size-4" aria-hidden="true" />
            Reset demo
          </button>
        </div>
      )}
    </div>
  );
}
