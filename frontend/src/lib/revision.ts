/** Turning a stored revision back into the body the API takes, with one position changed. */
import type { ExtraIn, PositionIn, PositionOut, QuoteDetail, RevisionIn } from "../api/types";

export function toPositionIn(p: PositionOut): PositionIn {
  return {
    ref: p.ref,
    construction_type: p.construction_type,
    width_mm: p.width_mm,
    height_mm: p.height_mm,
    qty: p.qty,
    colour: p.colour,
    glass_build: p.glass_build,
    openings: [...p.openings],
    readings: p.readings ?? null,
    installation: p.installation,
  };
}

export function revisionBody(
  quote: QuoteDetail,
  change: { replace?: string; position?: PositionIn; remove?: string } = {},
): RevisionIn {
  const rev = quote.revision;
  let positions = rev.positions.map(toPositionIn);
  if (change.remove !== undefined) {
    positions = positions.filter((p) => p.ref !== change.remove);
  }
  if (change.position) {
    const at = positions.findIndex((p) => p.ref === (change.replace ?? change.position?.ref));
    if (at >= 0) positions[at] = change.position;
    else positions.push(change.position);
  }
  const extras: ExtraIn[] = rev.extra_lines.map((e) => ({ ...e }));
  return {
    margin_bp: rev.margin_bp,
    discount_cents: rev.discount_cents,
    discount_bp: rev.discount_bp,
    transport_km: rev.transport_km,
    valid_days: rev.valid_days,
    positions,
    extras,
  };
}

/** The next free name: P1, P2, … */
export function nextRef(quote: QuoteDetail): string {
  const used = new Set(quote.revision.positions.map((p) => p.ref));
  let n = quote.revision.positions.length + 1;
  while (used.has(`P${n}`)) n += 1;
  return `P${n}`;
}
