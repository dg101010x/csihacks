import { describe, expect, it } from "vitest";
import { formatDate } from "./format";

describe("formatDate", () => {
  it("does not shift a date-only string back a day in a negative-UTC-offset timezone", () => {
    // Regression test: new Date("2026-07-31") parses as UTC midnight: in any
    // timezone behind UTC (e.g. US Pacific, UTC-7/-8), .toLocaleDateString()
    // used to render this as "Jul 30". This must always read "Jul 31".
    expect(formatDate("2026-07-31")).toBe("Jul 31");
    expect(formatDate("2026-01-01")).toBe("Jan 1");
    expect(formatDate("2026-12-31")).toBe("Dec 31");
  });

  it("still handles full datetime strings correctly", () => {
    expect(formatDate("2026-07-27T09:00:00Z")).toBe("Jul 27");
  });
});
