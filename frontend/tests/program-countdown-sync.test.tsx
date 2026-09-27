import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProgramCountdown } from "@/components/program-countdown";

describe("shared program countdown", () => {
  it("uses the shared shell elapsed clock instead of starting a second timer", () => {
    render(<ProgramCountdown seconds={57} syncElapsedSeconds={12} />);
    expect(screen.getByRole("timer")).toHaveTextContent("0m 45s");
  });

  it("stays aligned when the shell clock advances", () => {
    const view = render(<ProgramCountdown seconds={57} syncElapsedSeconds={12} />);
    view.rerender(<ProgramCountdown seconds={57} syncElapsedSeconds={13} />);
    expect(screen.getByRole("timer")).toHaveTextContent("0m 44s");
  });
});
