"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  ClipboardList,
  FlaskConical,
  Landmark,
  LayoutGrid,
  RotateCcw,
  ScrollText,
  Scale,
  Database,
} from "lucide-react";
import { cn } from "@relief/design-system";
import { useResetScenario } from "@/domain/hooks";

interface PaletteItem {
  id: string;
  label: string;
  group: "Navigate" | "Actions";
  icon: React.ComponentType<{ className?: string }>;
  run: () => void;
}

/** Section 5, item 7 — Cmd/Ctrl+K command palette for navigation and demo actions. */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const reset = useResetScenario();

  const items: PaletteItem[] = useMemo(
    () => [
      { id: "nav-command-center", label: "Go to Command Center", group: "Navigate", icon: LayoutGrid, run: () => router.push("/") },
      { id: "nav-timeline", label: "Go to Timeline", group: "Navigate", icon: Activity, run: () => router.push("/timeline") },
      { id: "nav-scenario-lab", label: "Go to Scenario Lab", group: "Navigate", icon: FlaskConical, run: () => router.push("/scenario-lab") },
      { id: "nav-interventions", label: "Go to Interventions", group: "Navigate", icon: ClipboardList, run: () => router.push("/interventions") },
      { id: "nav-constitution", label: "Go to Constitution", group: "Navigate", icon: Scale, run: () => router.push("/constitution") },
      { id: "nav-audit", label: "Go to Audit", group: "Navigate", icon: ScrollText, run: () => router.push("/audit") },
      { id: "nav-providers", label: "Go to Providers", group: "Navigate", icon: Landmark, run: () => router.push("/providers") },
      { id: "nav-data", label: "Go to Data", group: "Navigate", icon: Database, run: () => router.push("/data") },
      { id: "action-reset", label: "Reset demo", group: "Actions", icon: RotateCcw, run: () => reset.mutate() },
    ],
    [router, reset],
  );

  const filtered = items.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));

  const close = () => {
    dialogRef.current?.close();
    setOpen(false);
    setQuery("");
    setActiveIndex(0);
  };

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    }
    document.addEventListener("keydown", handleShortcut);
    return () => document.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    if (open) {
      dialogRef.current?.showModal();
      inputRef.current?.focus();
    }
  }, [open]);

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      const item = filtered[activeIndex];
      if (item) {
        item.run();
        close();
      }
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-muted-foreground transition-colors duration-fast hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        Search or jump to…
        <kbd className="rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
          ⌘K
        </kbd>
      </button>

      <dialog
        ref={dialogRef}
        onClose={close}
        className="w-full max-w-lg rounded-lg border border-border bg-surface p-0 shadow-overlay backdrop:bg-deep-ink/40"
      >
        <div className="flex flex-col">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setActiveIndex(0);
            }}
            onKeyDown={handleKeyDown}
            placeholder="Search or jump to…"
            aria-label="Command palette search"
            className="border-b border-border bg-transparent px-4 py-3 text-sm text-foreground outline-none placeholder:text-muted-foreground"
          />
          <ul role="listbox" className="max-h-80 overflow-y-auto p-2">
            {filtered.length === 0 && <li className="px-2 py-4 text-center text-sm text-muted-foreground">No matches.</li>}
            {filtered.map((item, index) => {
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={index === activeIndex}
                    onMouseEnter={() => setActiveIndex(index)}
                    onClick={() => {
                      item.run();
                      close();
                    }}
                    className={cn(
                      "flex w-full items-center gap-2.5 rounded-sm px-2 py-2 text-left text-sm text-foreground",
                      index === activeIndex && "bg-accent text-accent-foreground",
                    )}
                  >
                    <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      </dialog>
    </>
  );
}
