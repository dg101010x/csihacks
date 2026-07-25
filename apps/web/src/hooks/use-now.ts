"use client";

import { useState } from "react";

/** A stable "now" timestamp captured once at mount — avoids calling the
 * impure Date.now() directly during render (react-hooks/purity). */
export function useNow(): number {
  const [now] = useState(() => Date.now());
  return now;
}
