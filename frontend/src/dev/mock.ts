/**
 * DEV ONLY: a stand-in API for looking at the screens without a database (`npm run dev`, then
 * open `/?mock`). The quote and calculation in fixture.json come from the real engine run on the
 * demo workshop's invented sheet and prices. `/engine/measure` here is a rough stand-in for the
 * engine's gap table; the real rule lives only in the backend. Never imported in a build.
 */
import fixture from "./fixture.json";

type Json = Record<string, unknown>;

const me = {
  user_id: "00000000-0000-0000-0000-000000000001",
  email: "demo@example.invalid",
  role: "owner",
  workshop_id: "00000000-0000-0000-0000-0000000000aa",
  workshop_name: "Probna radionica (izmišljeni podaci)",
  is_demo: true,
  totp_ok: true,
  csrf_token: "dev",
};

const clients = [
  { id: "c1", name: "Probni klijent", phone: "+000 00 000 001", place: "Probno mjesto", erased_at: null },
  { id: "c2", name: "Drugi probni klijent", phone: "", place: "Drugo mjesto", erased_at: null },
];
const system = { id: "s1", key: "sample", brand: "Probni profil", series: "70 (izmišljeni)", depth_mm: 70, enabled: true };

function revision(positions: unknown[]) {
  return {
    revision_no: 1,
    margin_bp: 2500,
    discount_cents: 0,
    discount_bp: 0,
    vat_bp: 0,
    valid_days: 15,
    transport_km: 12,
    locked_at: null,
    price_list_version_id: fixture.priceList.id,
    system_sheet_version_id: "sheet",
    positions,
    extra_lines: fixture.extras,
  };
}

const total = (fixture.calculation as { price: { total_cents: number } }).price.total_cents;
const quotes: Json[] = [
  { id: "q1", number: "2026-0007", client_id: "c1", client_name: "Probni klijent", status: "draft", revision_no: 1, sent_at: null, accepted_at: null, valid_until: null, total_cents: null, paid_cents: 0, revision: revision(fixture.positions), revisions: [1] },
  { id: "q2", number: "2026-0006", client_id: "c2", client_name: "Drugi probni klijent", status: "sent", revision_no: 1, sent_at: "2026-11-10T09:00:00Z", accepted_at: null, valid_until: "2026-11-25", total_cents: 84250, paid_cents: 0, revision: revision(fixture.positions.slice(0, 2)), revisions: [1] },
  { id: "q3", number: "2026-0005", client_id: "c1", client_name: "Probni klijent", status: "accepted", revision_no: 1, sent_at: "2026-11-02T09:00:00Z", accepted_at: "2026-11-04T15:00:00Z", valid_until: "2026-11-17", total_cents: total, paid_cents: Math.round(total / 2), revision: { ...revision(fixture.positions), locked_at: "2026-11-04T15:00:00Z" }, revisions: [1] },
];

const GAPS = [
  [1500, 10, 15],
  [2500, 15, 20],
  [3500, 20, 25],
] as const;

function gap(side: number, colour: string): number {
  const row = GAPS.find(([max]) => side <= max) ?? GAPS[2];
  return colour === "white" ? row[1] : row[2];
}

function measure(body: { readings: { widths: number[]; heights: number[] }; colour: string }) {
  const w = Math.min(...body.readings.widths);
  const h = Math.min(...body.readings.heights);
  const gw = gap(w, body.colour);
  const gh = gap(h, body.colour);
  const spread = (values: number[]) => Math.max(...values) - Math.min(...values);
  return {
    opening_width_mm: w,
    opening_height_mm: h,
    gap_width_mm: gw,
    gap_height_mm: gh,
    width_mm: w - 2 * gw,
    height_mm: h - 2 * gh,
    formula_width: `W - 2g = ${w} - 2 x ${gw} = ${w - 2 * gw}`,
    formula_height: `H - 2g = ${h} - 2 x ${gh} = ${h - 2 * gh}`,
    warnings: [
      ...(spread(body.readings.widths) > 10 ? ["width"] : []),
      ...(spread(body.readings.heights) > 10 ? ["height"] : []),
    ],
  };
}

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function route(method: string, path: string, body: Json): Response {
  const parts = path.split("?")[0]?.split("/").filter(Boolean) ?? [];
  const [a, b, c, d, e] = parts;
  if (a === "auth") return b === "logout" ? reply(204) : reply(200, me);
  if (a === "quotes" && !b) {
    if (method === "POST") {
      const created = { ...quotes[0], id: `q${quotes.length + 1}`, number: `2026-000${quotes.length + 1}`, revision: revision([]), status: "draft" };
      quotes.unshift(created);
      return reply(201, created);
    }
    return reply(200, quotes);
  }
  const quote = quotes.find((q) => q.id === b);
  if (a === "quotes" && quote) {
    if (c === "revisions" && e === "calculate") return reply(200, fixture.calculation);
    if (c === "revisions" && d && method === "PUT") {
      quote.revision = { ...(quote.revision as Json), ...body, extra_lines: body.extras };
      return reply(200, quote);
    }
    if (c === "status") {
      quote.status = body.status;
      return reply(200, quote);
    }
    if (c === "payments") return reply(200, []);
    return reply(200, quote);
  }
  if (a === "engine" && b === "measure") return reply(200, measure(body as never));
  if (a === "clients") return method === "POST" ? reply(201, { id: "c9", erased_at: null, ...body }) : reply(200, clients);
  if (a === "systems") return reply(200, [system]);
  if (a === "price-lists") return reply(200, [fixture.priceList]);
  if (a === "suppliers") return reply(200, fixture.suppliers);
  if (a === "settings") return reply(200, fixture.settings);
  return reply(404, { title: "not found", status: 404, detail: path });
}

/** The tab keeps the demo's quotes, so a reload stays in the demo with what was entered. */
export const MOCK_STORE = "mjera.mock";

function restore(): void {
  try {
    const saved = window.sessionStorage.getItem(MOCK_STORE);
    if (saved) quotes.splice(0, quotes.length, ...(JSON.parse(saved) as Json[]));
  } catch {
    // Blocked storage: the demo starts fresh on every load.
  }
}

function persist(): void {
  try {
    window.sessionStorage.setItem(MOCK_STORE, JSON.stringify(quotes));
  } catch {
    // Blocked storage: changes last until the next reload.
  }
}

export function installMock(): void {
  restore();
  persist();
  const real = window.fetch.bind(window);
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const path = url.replace(/^.*\/api\/v1\//, "");
    if (!url.includes("/api/v1/")) return real(input, init);
    await new Promise((resolve) => setTimeout(resolve, 150));
    const body = init?.body ? (JSON.parse(init.body as string) as Json) : {};
    const method = init?.method ?? "GET";
    const response = route(method, path, body);
    if (method !== "GET") persist();
    return response;
  };
}
