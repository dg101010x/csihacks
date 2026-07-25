"use client";

import { useEffect, useState } from "react";

/**
 * Starts the Mock Service Worker before rendering children (Section 24: the
 * mock application must support the complete demonstration before the real
 * API exists). Gated so no request races the worker's registration.
 */
const mswEnabled = process.env.NEXT_PUBLIC_USE_MSW !== "false";

export function MswProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(!mswEnabled);

  useEffect(() => {
    if (!mswEnabled) return;
    let cancelled = false;
    import("@relief/test-fixtures/msw/browser").then(({ worker }) =>
      worker.start({ onUnhandledRequest: "bypass" }).then(() => {
        if (!cancelled) setReady(true);
      }),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) return null;
  return <>{children}</>;
}
