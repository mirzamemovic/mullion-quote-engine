import { describe, expect, it } from "vitest";

import { csrfToken } from "../api/client";
import { day, money, moneyInput, parseMoney, percent, size } from "./format";
import { cutLabel, workshopLabel } from "./labels";
import { cleanDigits, complete, emptyReadings, isFinished, nextSlot, parseReading, smallestSlots } from "./readings";
import { nextRef, revisionBody } from "./revision";
import type { QuoteDetail } from "../api/types";

describe("format", () => {
  it("formats cents in both languages without floats", () => {
    expect(money(123456, "bs")).toBe("1.234,56 €");
    expect(money(123456, "en")).toBe("€1,234.56");
    expect(money(5, "bs")).toBe("0,05 €");
    expect(money(-2500, "bs")).toBe("−25,00 €");
  });

  it("writes every workshop currency, the euro sign first only in English", () => {
    expect(money(123456, "en", "BAM")).toBe("1,234.56 KM");
    expect(money(123456, "bs", "BAM")).toBe("1.234,56 KM");
    expect(money(99, "en", "RSD")).toBe("0.99 RSD");
  });

  it("reads typed amounts as exact cents and writes them back", () => {
    expect(parseMoney("21,60")).toBe(2160);
    expect(parseMoney("21.6")).toBe(2160);
    expect(parseMoney(" 1 234 ")).toBe(123400);
    expect(parseMoney("0.1")).toBe(10);
    for (const bad of ["", "-5", "1.234,50", "21.605", "abc"]) expect(parseMoney(bad)).toBeNull();
    expect(moneyInput(2160, "bs")).toBe("21,60");
    expect(moneyInput(2160, "en")).toBe("21.60");
  });

  it("formats basis points as percent", () => {
    expect(percent(2500, "bs")).toBe("25 %");
    expect(percent(1850, "bs")).toBe("18,5 %");
    expect(percent(1805, "en")).toBe("18.05 %");
  });

  it("writes sizes and dates the trade's way", () => {
    expect(size(1368, 1171)).toBe("1368 × 1171");
    expect(day("2026-11-28", "bs")).toBe("28.11.2026.");
    expect(day("2026-11-28", "en")).toBe("28 Nov 2026");
  });
});

describe("readings", () => {
  it("keeps only up to four digits", () => {
    expect(cleanDigits("1 4a02 9")).toBe("1402");
  });

  it("accepts 300 to 4000 mm", () => {
    expect(parseReading("299")).toBeNull();
    expect(parseReading("300")).toBe(300);
    expect(parseReading("4000")).toBe(4000);
    expect(parseReading("4001")).toBeNull();
  });

  it("moves on once one more digit could not be valid", () => {
    expect(isFinished("830")).toBe(true); // 8300 would be too large
    expect(isFinished("350")).toBe(false); // 3500 is still possible
    expect(isFinished("1402")).toBe(true);
    expect(isFinished("14")).toBe(false);
  });

  it("follows the measuring order and circles the smallest of each side", () => {
    expect(nextSlot("wBottom")).toBe("hLeft");
    expect(nextSlot("hRight")).toBeNull();
    const r = { ...emptyReadings(), wTop: "1402", wMiddle: "1398", wBottom: "1400", hLeft: "1201", hRight: "1199" };
    expect([...smallestSlots(r)].sort()).toEqual(["hRight", "wMiddle"]);
    expect(complete(r)).toBeNull();
    expect(complete({ ...r, hMiddle: "1200" })).toEqual({ widths: [1402, 1398, 1400], heights: [1201, 1200, 1199] });
  });
});

describe("workshop labels", () => {
  it("puts engine labels into the trade's words", () => {
    expect(workshopLabel("left sash bead horizontal", "bs")).toBe("lijevo krilo lajsna horizontalno");
    expect(workshopLabel("false mullion", "bs")).toBe("štulp");
    expect(workshopLabel("frame/white bars", "bs")).toBe("štok · bijela šipke");
    expect(workshopLabel("hardware tilt_turn_left", "bs")).toBe("okov okretno-nagibno lijevo");
    expect(workshopLabel("hardware tilt_turn_left", "en")).toBe("hardware tilt-turn left");
    expect(cutLabel("Kuhinja frame left", "Kuhinja", "bs")).toBe("Kuhinja · štok lijevo");
  });

  it("lets an unknown word through", () => {
    expect(workshopLabel("frame widget", "bs")).toBe("štok widget");
  });
});

describe("csrf", () => {
  it("reads the token from its cookie", () => {
    expect(csrfToken("a=1; __Host-csrf=abc%3D; b=2")).toBe("abc=");
    expect(csrfToken("a=1")).toBeUndefined();
  });
});

describe("revision body", () => {
  const position = {
    ref: "P1",
    construction_type: "fixed",
    width_mm: 600,
    height_mm: 900,
    qty: 1,
    colour: "white" as const,
    glass_build: "4-16-4",
    openings: ["fixed" as const],
    readings: null,
    installation: { install: true, ral: false, old_window_removal: false, wall_repair: false },
  };
  const quote = {
    revision: {
      margin_bp: 2500,
      discount_cents: 0,
      discount_bp: 0,
      transport_km: 40,
      valid_days: 15,
      positions: [position],
      extra_lines: [],
    },
  } as unknown as QuoteDetail;

  it("replaces, adds and removes positions by ref", () => {
    expect(revisionBody(quote, { replace: "P1", position: { ...position, qty: 3 } }).positions[0]?.qty).toBe(3);
    expect(revisionBody(quote, { position: { ...position, ref: "P2" } }).positions).toHaveLength(2);
    expect(revisionBody(quote, { remove: "P1" }).positions).toHaveLength(0);
    expect(revisionBody(quote).transport_km).toBe(40);
  });

  it("names the next window", () => {
    expect(nextRef(quote)).toBe("P2");
  });
});
