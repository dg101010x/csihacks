import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("is keyboard operable (Section 27, item 1)", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Approve</Button>);
    const button = screen.getByRole("button", { name: "Approve" });
    button.focus();
    expect(button).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("disables interaction and announces busy state while loading", () => {
    render(<Button isLoading>Submitting</Button>);
    const button = screen.getByRole("button", { name: "Submitting" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
});
