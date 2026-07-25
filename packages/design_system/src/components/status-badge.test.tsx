import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./status-badge";
import { createStatusDescriptor } from "../accessibility";

describe("StatusBadge", () => {
  it("always renders both text and an icon (Section 19, rules 7-8)", () => {
    render(
      <StatusBadge
        descriptor={createStatusDescriptor({ tone: "risk", label: "Reserve violation projected", icon: "alert-octagon" })}
      />,
    );
    expect(screen.getByText("Reserve violation projected")).toBeInTheDocument();
    // lucide icons render as <svg aria-hidden="true"> — assert one is present alongside the text.
    const badge = screen.getByText("Reserve violation projected").closest("span");
    expect(badge?.querySelector("svg")).toBeInTheDocument();
  });

  it("rejects a status descriptor built without a label", () => {
    expect(() => createStatusDescriptor({ tone: "risk", label: "  ", icon: "alert-octagon" })).toThrow();
  });
});
