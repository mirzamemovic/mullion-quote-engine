/** The last profile system, colour and glass, remembered on this phone (PLAN.md section 7). */
import type { Colour } from "../api/types";

const KEY = "mjera.last";

export interface LastChoices {
  systemId?: string;
  colour?: Colour;
  glass?: string;
}

export function lastChoices(): LastChoices {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as LastChoices) : {};
  } catch {
    return {};
  }
}

export function remember(choices: LastChoices): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify({ ...lastChoices(), ...choices }));
  } catch {
    // Storage blocked: nothing is remembered, everything still works.
  }
}
