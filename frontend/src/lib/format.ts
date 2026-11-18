/** Display formats. Money is whole cents and percentages whole basis points, never floats. */

const MINUS = "−";

/** The currencies a workshop can pick. Every one has two minor digits (cents). */
export const CURRENCIES = ["EUR", "BAM", "RSD", "ALL", "MKD"] as const;
export type Currency = (typeof CURRENCIES)[number];
const SYMBOLS: Record<Currency, string> = { EUR: "€", BAM: "KM", RSD: "RSD", ALL: "ALL", MKD: "MKD" };

let activeCurrency: Currency = "EUR";

/** The workshop's currency, set once the app knows who is logged in. */
export function setCurrency(code: string): void {
  activeCurrency = (CURRENCIES as readonly string[]).includes(code) ? (code as Currency) : "EUR";
}

export function currencySymbol(currency: Currency = activeCurrency): string {
  return SYMBOLS[currency];
}

/**
 * 123456 minor units -> "€1,234.56" / "1.234,56 €" for euros, "1,234.56 KM" / "1.234,56 KM"
 * for the others. Integer maths only.
 */
export function money(cents: number, language: string, currency: Currency = activeCurrency): string {
  const negative = cents < 0;
  const whole = Math.trunc(Math.abs(cents) / 100);
  const rest = Math.abs(cents) % 100;
  const english = language.startsWith("en");
  const groups = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, english ? "," : ".");
  const amount = `${groups}${english ? "." : ","}${String(rest).padStart(2, "0")}`;
  const sign = negative ? MINUS : "";
  if (currency === "EUR" && english) return `${sign}€${amount}`;
  return `${sign}${amount} ${SYMBOLS[currency]}`;
}

/**
 * What someone typed as an amount ("21,60", "21.6", "21") as exact minor units, or ``null`` when
 * it is not a plain amount. Read as text, never through a float, so 0.1 + 0.2 never happens.
 */
export function parseMoney(text: string): number | null {
  const value = text.trim().replace(/\s/g, "");
  const match = /^(\d{1,9})(?:[.,](\d{1,2}))?$/.exec(value);
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
}

/** Minor units as an editable amount: 2160 -> "21,60" (Bosnian) or "21.60" (English). */
export function moneyInput(cents: number, language: string): string {
  const text = `${Math.trunc(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
  return language.startsWith("en") ? text : text.replace(".", ",");
}

/** Basis points as a percentage without floats: 2500 -> "25 %", 1850 -> "18,5 %". */
export function percent(bp: number, language: string): string {
  const whole = Math.trunc(bp / 100);
  const rest = Math.abs(bp % 100);
  const decimals = rest === 0 ? "" : `${language.startsWith("en") ? "." : ","}${String(rest).padStart(2, "0").replace(/0$/, "")}`;
  return `${whole}${decimals} %`;
}

/** A length in whole millimetres, as the trade writes it. */
export function mm(value: number): string {
  return String(value);
}

/** "1368 × 1171" */
export function size(width: number, height: number): string {
  return `${width} × ${height}`;
}

/** The ISO date (YYYY-MM-DD) of a Date in local time, for date inputs and the API. */
export function isoDate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** "2026-11-28" -> "28.11.2026." (Bosnian) or "28 Nov 2026" (English). */
export function day(iso: string, language: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-");
  if (!y || !m || !d) return iso;
  if (language.startsWith("en")) {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${Number(d)} ${months[Number(m) - 1] ?? m} ${y}`;
  }
  return `${Number(d)}.${Number(m)}.${y}.`;
}
