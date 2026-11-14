/**
 * DEV ONLY: a stand-in for the database while there is none (`npm run dev`, then open `/?mock`).
 *
 * Quotes and clients live in this browser tab. Everything the engine decides comes from the real
 * engine through the backend's development endpoints (`/api/v1/dev/*`, started with
 * `QUOTE_ENGINE_DEV_DEMO=1`): the catalogue of profile systems and market-estimate prices, every
 * calculation and every measurement. Never imported in a build.
 */
import fixture from "./fixture.json";

type Json = Record<string, unknown>;
const DEV = "/api/v1/dev";
export const MOCK_STORE = "mjera.mock";

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

interface Catalogue {
  systems: Json[];
  price_list: Json;
  suppliers: Json[];
  settings: Json;
}

interface State {
  clients: Json[];
  quotes: Json[];
}

let catalogue: Catalogue | null = null;
let realFetch: typeof window.fetch = window.fetch.bind(window);
const state: State = { clients: [], quotes: [] };

function revision(positions: unknown[], systemKey: string, extras: unknown[] = []): Json {
  return {
    revision_no: 1,
    margin_bp: 2500,
    discount_cents: 0,
    discount_bp: 0,
    vat_bp: 0,
    valid_days: 15,
    transport_km: 12,
    locked_at: null,
    price_list_version_id: "demo-prices",
    system_sheet_version_id: systemKey,
    positions,
    extra_lines: extras,
  };
}

function seed(): void {
  const first = (catalogue?.systems[0]?.id as string | undefined) ?? "";
  const aluminium = catalogue?.systems.find((s) => s.material === "aluminium");
  const premium = (aluminium?.id as string | undefined) ?? first;
  state.clients = [
    { id: "c1", name: "Probni klijent", phone: "+000 00 000 001", place: "Probno mjesto", erased_at: null },
    { id: "c2", name: "Drugi probni klijent", phone: "", place: "Drugo mjesto", erased_at: null },
  ];
  const quote = (id: string, number: string, client: Json, status: string, system: string, positions: unknown[]) => ({
    id,
    number,
    client_id: client.id,
    client_name: client.name,
    status,
    system_key: system,
    revision_no: 1,
    sent_at: status === "draft" ? null : "2026-11-10T09:00:00Z",
    accepted_at: status === "accepted" ? "2026-11-12T15:00:00Z" : null,
    valid_until: status === "draft" ? null : "2026-11-25",
    total_cents: null,
    paid_cents: 0,
    revision: revision(positions, system),
    revisions: [1],
  });
  const [c1, c2] = state.clients as [Json, Json];
  state.quotes = [
    quote("q1", "2026-0007", c1, "draft", first, fixture.positions),
    quote("q2", "2026-0006", c2, "sent", premium, fixture.positions.slice(0, 2)),
    quote("q3", "2026-0005", c1, "accepted", first, fixture.positions),
  ];
}

function restore(): boolean {
  try {
    const saved = window.sessionStorage.getItem(MOCK_STORE);
    if (!saved) return false;
    Object.assign(state, JSON.parse(saved) as State);
    return state.quotes.length > 0;
  } catch {
    return false;
  }
}

function persist(): void {
  try {
    window.sessionStorage.setItem(MOCK_STORE, JSON.stringify(state));
  } catch {
    // Blocked storage: changes last until the next reload.
  }
}

function reply(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Ask the real engine (development endpoint); a missing backend is a clear 503, not a guess. */
async function engine(path: string, body?: unknown): Promise<Response> {
  try {
    const response = await realFetch(`${DEV}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 404) {
      return reply(503, {
        title: "engine not running",
        status: 503,
        detail: "Pokreni backend s QUOTE_ENGINE_DEV_DEMO=1 (demo bez baze).",
      });
    }
    return response;
  } catch {
    return reply(503, { title: "engine not running", status: 503, detail: "Backend ne radi." });
  }
}

function content(quote: Json): Json {
  const rev = quote.revision as Json;
  return {
    margin_bp: rev.margin_bp,
    discount_cents: rev.discount_cents,
    discount_bp: rev.discount_bp,
    transport_km: rev.transport_km,
    valid_days: rev.valid_days,
    positions: rev.positions,
    extras: rev.extra_lines,
  };
}

async function calculate(quote: Json): Promise<Response> {
  const response = await engine("/calculate", { system_key: quote.system_key, revision: content(quote) });
  if (response.ok) {
    const result = (await response.clone().json()) as { price: { total_cents: number } };
    if (quote.status !== "draft") quote.total_cents = result.price.total_cents;
  }
  return response;
}

async function route(method: string, path: string, body: Json): Promise<Response> {
  const parts = path.split("?")[0]?.split("/").filter(Boolean) ?? [];
  const [a, b, c, d, e] = parts;
  if (a === "auth") return b === "logout" ? reply(204) : reply(200, me);
  if (a === "quotes" && !b) {
    if (method === "POST") {
      const client = state.clients.find((x) => x.id === body.client_id) ?? state.clients[0] ?? {};
      const system = String(body.profile_system_id);
      const number = `2026-${String(8 + state.quotes.length).padStart(4, "0")}`;
      const created: Json = {
        id: `q${Date.now()}`,
        number,
        client_id: client.id,
        client_name: client.name,
        status: "draft",
        system_key: system,
        revision_no: 1,
        sent_at: null,
        accepted_at: null,
        valid_until: null,
        total_cents: null,
        paid_cents: 0,
        revision: revision([], system),
        revisions: [1],
      };
      state.quotes.unshift(created);
      return reply(201, created);
    }
    return reply(200, state.quotes);
  }
  const quote = state.quotes.find((q) => q.id === b);
  if (a === "quotes" && quote) {
    if (c === "revisions" && e === "calculate") {
      const positions = (quote.revision as Json).positions as unknown[];
      if (positions.length === 0) return reply(422, { title: "invalid input", status: 422, detail: "Nema prozora." });
      return calculate(quote);
    }
    if (c === "revisions" && d && method === "PUT") {
      quote.revision = { ...(quote.revision as Json), ...body, extra_lines: body.extras };
      return reply(200, quote);
    }
    if (c === "status") {
      quote.status = body.status;
      if (body.status === "sent") {
        quote.sent_at = new Date().toISOString();
        quote.valid_until = new Date(Date.now() + 15 * 86_400_000).toISOString().slice(0, 10);
      }
      if (body.status === "accepted") quote.accepted_at = new Date().toISOString();
      await calculate(quote);
      return reply(200, quote);
    }
    if (c === "payments") return reply(200, []);
    return reply(200, quote);
  }
  if (a === "engine" && b === "measure") return engine("/measure", body);
  if (a === "clients") {
    if (method === "POST") {
      const created = { id: `c${Date.now()}`, erased_at: null, phone: "", place: "", ...body };
      state.clients.push(created);
      return reply(201, created);
    }
    return reply(200, state.clients);
  }
  if (!catalogue) return reply(503, { title: "engine not running", status: 503, detail: "Nema kataloga." });
  if (a === "systems") return reply(200, catalogue.systems);
  if (a === "price-lists") return reply(200, [catalogue.price_list]);
  if (a === "suppliers") return reply(200, catalogue.suppliers);
  if (a === "settings") return reply(200, catalogue.settings);
  return reply(404, { title: "not found", status: 404, detail: path });
}

export async function installMock(): Promise<void> {
  realFetch = window.fetch.bind(window);
  const response = await engine("/catalogue");
  catalogue = response.ok ? ((await response.json()) as Catalogue) : null;
  if (!restore()) seed();
  persist();
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    if (!url.includes("/api/v1/") || url.includes("/api/v1/dev/")) return realFetch(input, init);
    const path = url.replace(/^.*\/api\/v1\//, "");
    const body = init?.body ? (JSON.parse(init.body as string) as Json) : {};
    const method = init?.method ?? "GET";
    const answer = await route(method, path, body);
    if (method !== "GET") persist();
    return answer;
  };
}
