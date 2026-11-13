import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WindowDrawing, fieldCount } from "./WindowDrawing";

describe("WindowDrawing", () => {
  it("puts the handle opposite the hinges, seen from inside", () => {
    const left = render(<WindowDrawing type="single_sash_tilt_turn" width={800} height={1400} openings={["tilt_turn_left"]} />);
    expect(left.container.querySelector("[data-handle]")?.getAttribute("data-handle")).toBe("right");
    const right = render(<WindowDrawing type="single_sash_tilt_turn" width={800} height={1400} openings={["turn_right"]} />);
    expect(right.container.querySelector("[data-handle]")?.getAttribute("data-handle")).toBe("left");
  });

  it("draws tilt as a dashed mark only for tilt-and-turn", () => {
    const { container } = render(
      <WindowDrawing type="two_field_t_mullion" width={1400} height={1400} openings={["turn_left", "tilt_turn_right"]} />,
    );
    expect(container.querySelectorAll("[stroke-dasharray]")).toHaveLength(1);
    expect(container.querySelectorAll("[data-handle]")).toHaveLength(2);
  });

  it("has no handle and no sash on a fixed window", () => {
    const { container } = render(<WindowDrawing type="fixed" width={600} height={900} openings={["fixed"]} />);
    expect(container.querySelector("[data-handle]")).toBeNull();
  });

  it("knows the fields of every type", () => {
    expect(fieldCount("two_sash_false_mullion")).toBe(2);
    expect(fieldCount("balcony_door_tilt_turn")).toBe(1);
  });

  it("is a labelled image when titled, hidden decoration otherwise", () => {
    const titled = render(<WindowDrawing type="fixed" width={600} height={900} openings={["fixed"]} title="Fiksni" />);
    expect(titled.getByRole("img", { name: "Fiksni" })).toBeInTheDocument();
  });
});
