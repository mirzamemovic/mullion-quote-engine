/** Display formats. Money is whole cents and percentages whole basis points, never floats. */

const MINUS = "−";

/** 123456 cents -> "1.234,56 €" (Bosnian) or "€1,234.56" (English). Integer maths only. */
export function euros(cents: number, language: string): string {
  const negative = cents < 0;
  const whole = Math.trunc(Math.abs(cents) / 100);
  const rest = Math.abs(cents) % 100;
  const english = language.startsWith("en");
  const groups = String(whole).replace(/\B(?=(\d{3})+(?!\d))/g, english ? "," : ".");
  const amount = `${groups}${english ? "." : ","}${String(rest).padStart(2, "0")}`;
  const sign = negative ? MINUS : "";
  return english ? `${sign}€${amount}` : `${sign}${amount} €`;
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
