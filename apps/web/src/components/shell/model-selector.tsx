"use client";

import { useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useModels } from "@/domain/hooks";

const STORAGE_KEY = "relief.forecast-model";
const CHANGE_EVENT = "relief-forecast-model-change";

function subscribe(onStoreChange: () => void) {
  window.addEventListener(CHANGE_EVENT, onStoreChange);
  window.addEventListener("storage", onStoreChange);
  return () => {
    window.removeEventListener(CHANGE_EVENT, onStoreChange);
    window.removeEventListener("storage", onStoreChange);
  };
}

export function ModelSelector() {
  const models = useModels();
  const queryClient = useQueryClient();
  const selected = useSyncExternalStore(
    subscribe,
    () => window.localStorage.getItem(STORAGE_KEY) ?? "deterministic",
    () => "deterministic",
  );

  const options = models.data ?? [];
  const current = options.find((model) => model.id === selected);
  const effectiveSelection = current?.selectable === false ? "deterministic" : selected;

  return (
    <label className="flex min-h-11 min-w-0 items-center gap-2 rounded-md border border-border bg-surface px-2 text-xs text-muted-foreground">
      <span className="sr-only whitespace-nowrap xl:not-sr-only">Forecast model</span>
      <select
        aria-label="Forecast model"
        className="min-w-0 max-w-28 bg-transparent font-medium text-foreground outline-none sm:max-w-44 xl:max-w-52"
        value={effectiveSelection}
        onChange={(event) => {
          const value = event.target.value;
          window.localStorage.setItem(STORAGE_KEY, value);
          window.dispatchEvent(new Event(CHANGE_EVENT));
          void queryClient.invalidateQueries({ queryKey: ["relief", "forecast"] });
        }}
      >
        {options.map((model) => (
          <option key={model.id} value={model.id} disabled={!model.selectable}>
            {model.name}
            {model.lifecycle === "shadow" ? " · Shadow" : ""}
            {model.status === "training" ? " · Training" : ""}
            {model.status === "unavailable" ? " · Offline" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
