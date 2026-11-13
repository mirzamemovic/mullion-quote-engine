/**
 * The six readings of one wall opening, in the order the owner takes them: widths top, middle,
 * bottom, then heights left, middle, right. The engine decides the window size; this only helps
 * typing (when to jump to the next slot) and marks the reading that counts (the smallest).
 */
export const READING_MIN = 300;
export const READING_MAX = 4000;

export type SlotId = "wTop" | "wMiddle" | "wBottom" | "hLeft" | "hMiddle" | "hRight";
export const SLOT_ORDER: SlotId[] = ["wTop", "wMiddle", "wBottom", "hLeft", "hMiddle", "hRight"];
export const WIDTH_SLOTS: SlotId[] = ["wTop", "wMiddle", "wBottom"];
export const HEIGHT_SLOTS: SlotId[] = ["hLeft", "hMiddle", "hRight"];

export type Readings = Record<SlotId, string>;

export const emptyReadings = (): Readings => ({
  wTop: "",
  wMiddle: "",
  wBottom: "",
  hLeft: "",
  hMiddle: "",
  hRight: "",
});

/** Only digits, at most four of them. */
export function cleanDigits(raw: string): string {
  return raw.replace(/\D/g, "").slice(0, 4);
}

export function parseReading(text: string): number | null {
  if (!/^\d{3,4}$/.test(text)) return null;
  const value = Number(text);
  return value >= READING_MIN && value <= READING_MAX ? value : null;
}

/** True when one more digit could not make a valid reading, so typing can move on. */
export function isFinished(text: string): boolean {
  if (parseReading(text) === null) return false;
  return text.length === 4 || Number(text) * 10 > READING_MAX;
}

export function nextSlot(current: SlotId): SlotId | null {
  const index = SLOT_ORDER.indexOf(current);
  return SLOT_ORDER[index + 1] ?? null;
}

/** The slots holding the smallest valid reading of each dimension (the ones that count). */
export function smallestSlots(readings: Readings): Set<SlotId> {
  const result = new Set<SlotId>();
  for (const group of [WIDTH_SLOTS, HEIGHT_SLOTS]) {
    let best: SlotId | null = null;
    let bestValue = Infinity;
    for (const slot of group) {
      const value = parseReading(readings[slot]);
      if (value !== null && value < bestValue) {
        best = slot;
        bestValue = value;
      }
    }
    if (best !== null) result.add(best);
  }
  return result;
}

/** All six readings as numbers, or ``null`` while any is missing or out of range. */
export function complete(readings: Readings): { widths: number[]; heights: number[] } | null {
  const widths = WIDTH_SLOTS.map((slot) => parseReading(readings[slot]));
  const heights = HEIGHT_SLOTS.map((slot) => parseReading(readings[slot]));
  if ([...widths, ...heights].some((value) => value === null)) return null;
  return { widths: widths as number[], heights: heights as number[] };
}

export function fromStored(stored: { widths: number[]; heights: number[] } | null | undefined): Readings {
  const readings = emptyReadings();
  if (!stored) return readings;
  WIDTH_SLOTS.forEach((slot, i) => (readings[slot] = String(stored.widths[i] ?? "")));
  HEIGHT_SLOTS.forEach((slot, i) => (readings[slot] = String(stored.heights[i] ?? "")));
  return readings;
}
