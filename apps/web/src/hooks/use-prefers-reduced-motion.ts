"use client";

import { useEffect, useState } from "react";
import { prefersReducedMotion } from "@relief/design-system";

/** Section 21.3 item 9, Section 27 item 7 — reduced motion mode, reactively. */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => prefersReducedMotion());

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = () => setReduced(mql.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return reduced;
}
