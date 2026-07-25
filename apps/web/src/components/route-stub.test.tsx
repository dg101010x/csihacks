import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RouteStub } from "./route-stub";

describe("RouteStub", () => {
  it("renders the title and description", () => {
    render(<RouteStub phase="Route: /demo" title="Shock simulator" description="Baseline state." />);
    expect(screen.getByRole("heading", { name: "Shock simulator" })).toBeInTheDocument();
    expect(screen.getByText("Baseline state.")).toBeInTheDocument();
  });
});
