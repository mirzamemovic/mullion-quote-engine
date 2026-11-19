import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../i18n";
import { setLanguage } from "../i18n";
import { App } from "../App";
import { emptyReadings, type Readings } from "../lib/readings";
import { DetailsStep } from "./position/DetailsStep";
import { MeasureStep } from "./position/MeasureStep";

function wrap(children: ReactNode, path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

const owner = {
  user_id: "u",
  email: "owner@example.invalid",
  role: "owner",
  workshop_id: "w",
  workshop_name: "Sample workshop",
  is_demo: false,
  sandbox_expires_at: null,
  currency: "EUR",
  language: "bs",
  totp_enabled: false,
  totp_ok: true,
  csrf_token: "c",
};

function json(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

beforeEach(() => setLanguage("bs"));
afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("asks a visitor to log in", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(401, { title: "log in first", status: 401 })));
    render(wrap(<App />, "/login"));

    expect(await screen.findByRole("heading", { name: "Prijava" })).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prijavi se" })).toBeInTheDocument();
  });

  it("says plainly when the login is wrong", async () => {
    const fetch = vi.fn((url: string) =>
      url.endsWith("/auth/me") ? json(401, {}) : json(401, { title: "login failed", detail: "wrong email or password", status: 401 }),
    );
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />, "/login"));
    fireEvent.change(await screen.findByLabelText("E-mail"), { target: { value: "owner@example.invalid" } });
    fireEvent.change(screen.getByLabelText("Lozinka"), { target: { value: "not-it" } });
    fireEvent.click(screen.getByRole("button", { name: "Prijavi se" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Pogrešan e-mail ili lozinka.");
  });

  it("shows the demo banner in the demo workshop", async () => {
    const me = { user_id: "u", email: "demo@example.invalid", role: "owner", workshop_id: "w", workshop_name: "Demo workshop (sample data)", is_demo: true, totp_ok: true, csrf_token: "c" };
    vi.stubGlobal("fetch", vi.fn((url: string) => (url.endsWith("/auth/me") ? json(200, me) : json(200, []))));
    render(wrap(<App />));

    expect(await screen.findByRole("note")).toHaveTextContent("DEMO");
    expect(await screen.findByText("Još nema ponuda.")).toBeInTheDocument();
  });

  it("asks the admin for the code before anything else", async () => {
    const me = { user_id: "u", email: "a@example.invalid", role: "admin", workshop_id: "w", workshop_name: "W", is_demo: false, totp_ok: false, csrf_token: "c" };
    vi.stubGlobal("fetch", vi.fn(() => json(200, me)));
    render(wrap(<App />));

    expect(await screen.findByRole("heading", { name: "Kod iz aplikacije" })).toBeInTheDocument();
  });
});

describe("Ways in", () => {
  it("shows a visitor what it does and opens a sample workshop in one tap", async () => {
    const fetch = vi.fn((url: string) =>
      url.endsWith("/auth/me")
        ? json(401, {})
        : url.endsWith("/sandbox")
          ? json(201, { ...owner, is_demo: true, sandbox_expires_at: "2099-01-01T00:00:00Z" })
          : json(200, []),
    );
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />));

    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("Ponude i planovi rezanja");
    expect(screen.getByRole("link", { name: "Prijava" })).toHaveAttribute("href", "/login");
    fireEvent.click(screen.getByRole("button", { name: "Isprobajte s probnim podacima" }));

    expect(await screen.findByRole("note")).toHaveTextContent("ne unosite prave podatke klijenata");
    const call = fetch.mock.calls.find(([url]) => url.endsWith("/sandbox")) as unknown as [string, RequestInit];
    expect(call[1].method).toBe("POST");
    expect(JSON.parse(call[1].body as string)).toEqual({ language: "bs" });
  });

  it("joins a workshop from an invite link, the token sent in the body only", async () => {
    const token = "t".repeat(43);
    const fetch = vi.fn((url: string) =>
      url.endsWith("/auth/me")
        ? json(401, {})
        : url.endsWith("/join/info")
          ? json(200, { workshop_name: "Sample workshop", role: "staff", expires_at: "2099-01-01T00:00:00Z" })
          : url.endsWith("/join")
            ? json(201, { ...owner, role: "staff" })
            : json(200, []),
    );
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />, `/join#${token}`));

    expect(await screen.findByRole("heading", { name: "Pridružite se: Sample workshop" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: "new@example.invalid" } });
    fireEvent.change(screen.getByLabelText("Izaberite lozinku"), { target: { value: "a-long-enough-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Pridruži se" }));

    await waitFor(() => expect(fetch.mock.calls.some(([url]) => url.endsWith("/join"))).toBe(true));
    const call = fetch.mock.calls.find(([url]) => url.endsWith("/join")) as unknown as [string, RequestInit];
    expect(call[0]).toBe("/api/v1/join");
    expect(JSON.parse(call[1].body as string)).toEqual({ token, email: "new@example.invalid", password: "a-long-enough-password" });
  });

  it("says an old invite link is not valid", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => (url.endsWith("/auth/me") ? json(401, {}) : json(404, { title: "not found", status: 404 }))));
    render(wrap(<App />, `/join#${"x".repeat(43)}`));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ova pozivnica više ne važi");
  });
});

describe("Setup checklist", () => {
  it("lists what is still missing, asked of the engine", async () => {
    const status = {
      ready: false,
      percent: 60,
      construction_types: ["fixed"],
      systems: [{ id: "s1", key: "sample", name: "Sample 70", material: "pvc", sheet: "draft", sheet_version: 1, missing: ["deductions.fixed_glass"], problem: null, done: false }],
      price_list_id: "p1",
      price_list_status: "published",
      prices_needed: 10,
      prices_missing: [{ kind: "labour", ref: "pvc/fixed/small", colour: null, unit: "piece", state: "missing", systems: [] }],
      foil_prices_missing: [],
      glass_priced: true,
      suppliers: 1,
      estimates: 3,
      openings_without_hardware_set: [],
    };
    vi.stubGlobal("fetch", vi.fn((url: string) => (url.endsWith("/auth/me") ? json(200, owner) : url.includes("/setup/status") ? json(200, status) : json(200, []))));
    render(wrap(<App />, "/workshop/setup"));

    expect(await screen.findByText("Prije prve ponude: 60% spremno.")).toBeInTheDocument();
    expect(screen.getByText("Sample 70: list sistema")).toBeInTheDocument();
    expect(screen.getByText("Nedostaje vrijednosti: 1")).toBeInTheDocument();
    expect(screen.getByText("Nedostaje 1 od 10")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("3 cijena su procjene tržišta");
    expect(screen.getByRole("link", { name: "Preuzmi cijene koje nedostaju (CSV)" })).toHaveAttribute("href", "/api/v1/setup/price-template.csv?price_list_id=p1");
  });
});

describe("DetailsStep", () => {
  const details = {
    ref: "P1",
    width: 0,
    height: 0,
    openings: ["tilt_turn_left" as const],
    glass: "",
    qty: 1,
    installation: { install: true, ral: false, old_window_removal: false, wall_repair: false },
  };

  it("says why the window cannot be saved yet", () => {
    render(
      wrap(
        <DetailsStep type="single_sash_tilt_turn" colour="white" details={details} glassBuilds={[]} sizeEditable busy={false} error={null} onChange={() => undefined} onSave={() => undefined} />,
      ),
    );

    const save = screen.getByRole("button", { name: "Spremi prozor" });
    expect(save).toBeDisabled();
    const reasons = document.getElementById(save.getAttribute("aria-describedby") ?? "");
    expect(reasons).toHaveTextContent("Upiši širinu i visinu");
    expect(reasons).toHaveTextContent("Odaberi staklo");
    expect(screen.getByText(/U cjenovniku nema stakla/)).toBeInTheDocument();
  });

  it("saves once the size and glass are there", () => {
    const onSave = vi.fn();
    render(
      wrap(
        <DetailsStep type="single_sash_tilt_turn" colour="white" details={{ ...details, width: 1200, height: 1400, glass: "4-16-4" }} glassBuilds={["4-16-4"]} sizeEditable busy={false} error={null} onChange={() => undefined} onSave={onSave} />,
      ),
    );

    const save = screen.getByRole("button", { name: "Spremi prozor" });
    expect(save).not.toHaveAttribute("aria-describedby");
    fireEvent.click(save);
    expect(onSave).toHaveBeenCalledOnce();
  });
});

function Measuring({ onDone }: { onDone: (r: unknown) => void }) {
  const [readings, setReadings] = useState<Readings>(emptyReadings());
  return (
    <MeasureStep readings={readings} onReadings={setReadings} colour="white" onColour={() => undefined} onDone={onDone} onSkip={() => undefined} />
  );
}

describe("MeasureStep", () => {
  it("jumps to the next slot, asks the engine and shows the window size", async () => {
    const measure = {
      opening_width_mm: 830, opening_height_mm: 1430, gap_width_mm: 10, gap_height_mm: 10,
      width_mm: 810, height_mm: 1410,
      formula_width: "830 - 2 x 10 = 810", formula_height: "1430 - 2 x 10 = 1410", warnings: [],
    };
    const fetch = vi.fn(() => json(200, measure));
    vi.stubGlobal("fetch", fetch);
    const onDone = vi.fn();
    render(wrap(<Measuring onDone={onDone} />));

    const top = screen.getByLabelText("Širina gore");
    top.focus();
    fireEvent.change(top, { target: { value: "830" } });
    expect(document.activeElement).toBe(screen.getByLabelText("Širina sredina"));

    const values: [string, string][] = [
      ["Širina sredina", "832"], ["Širina dolje", "831"],
      ["Visina lijevo", "1430"], ["Visina sredina", "1431"], ["Visina desno", "1432"],
    ];
    for (const [label, value] of values) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }

    expect(await screen.findByText(/810 × 1410/)).toBeInTheDocument();
    const [url, init] = fetch.mock.calls.at(-1) as unknown as [string, RequestInit];
    expect(url).toBe("/api/v1/engine/measure");
    expect(JSON.parse(init.body as string)).toEqual({ readings: { widths: [830, 832, 831], heights: [1430, 1431, 1432] }, colour: "white" });

    fireEvent.click(screen.getByRole("button", { name: "Kako je izračunato?" }));
    expect(screen.getByText("830 - 2 × 10 = 810")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Dalje/ }));
      await Promise.resolve();
    });
    await waitFor(() => expect(onDone).toHaveBeenCalledOnce());
  });
});

describe("Position editor", () => {
  const glass = (ref: string) => ({ item_kind: "glass", item_ref: ref });
  const quote = {
    id: "q1",
    number: "2026-0007",
    client_name: "Sample client",
    status: "draft",
    revision_no: 1,
    revision: {
      revision_no: 1,
      price_list_version_id: "used",
      positions: [
        {
          ref: "P1",
          construction_type: "fixed",
          width_mm: 1000,
          height_mm: 1000,
          qty: 1,
          colour: "white",
          glass_build: "4-16-4",
          openings: ["fixed"],
          readings: null,
          installation: { install: true, ral: false, old_window_removal: false, wall_repair: false },
        },
      ],
      extra_lines: [],
    },
  };
  // Newest first, as the API lists them: a draft being edited, then the list the quote uses.
  const lists = [
    { id: "draft", status: "draft", valid_from: "2026-01-02", entries: [glass("Draft-only glass")] },
    { id: "used", status: "published", valid_from: "2026-01-01", entries: [glass("4-12-4-12-4"), glass("4-16-4")] },
  ];

  it("offers the glass of the price list the quote is priced with", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) =>
        url.endsWith("/auth/me") ? json(200, owner) : url.endsWith("/quotes/q1") ? json(200, quote) : url.endsWith("/price-lists") ? json(200, lists) : json(200, []),
      ),
    );
    render(wrap(<App />, "/quotes/q1/positions/P1"));

    expect(await screen.findByRole("button", { name: "4-12-4-12-4" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "4-16-4" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("button", { name: "Draft-only glass" })).not.toBeInTheDocument();
  });
});

describe("Quote documents", () => {
  const position = {
    ref: "P1",
    construction_type: "fixed",
    width_mm: 1000,
    height_mm: 1000,
    qty: 1,
    colour: "white",
    glass_build: "4-16-4",
    openings: ["fixed"],
    readings: null,
    installation: { install: true, ral: false, old_window_removal: false, wall_repair: false },
  };
  const quote = {
    id: "q1",
    number: "2026-0007",
    client_id: "c",
    client_name: "Sample client",
    status: "draft",
    revision_no: 1,
    sent_at: null,
    accepted_at: null,
    valid_until: null,
    total_cents: null,
    paid_cents: 0,
    revisions: [1],
    revision: {
      revision_no: 1,
      margin_bp: 2500,
      discount_cents: 0,
      discount_bp: 0,
      vat_bp: 0,
      valid_days: 15,
      transport_km: 0,
      locked_at: null,
      price_list_version_id: "p",
      system_sheet_version_id: "s",
      positions: [position],
      extra_lines: [],
    },
  };
  const calculation = {
    cut_lists: { P1: { pieces: [], steel: [], glass: [], hardware_sets: [], gasket_mm: 0 } },
    plans: {},
    warnings: [],
    versions: {},
    price: {
      positions: [
        {
          ref: "P1",
          material: [],
          material_cents: 0,
          margin_cents: 0,
          labour_cents: 0,
          installation: [],
          installation_cents: 0,
          rounding_cents: 0,
          total_cents: 10_000,
          unit_price_cents: 10_000,
          area_mm2: 1_000_000,
          cents_per_m2: 10_000,
        },
      ],
      extras: [],
      transport_cents: 0,
      subtotal_cents: 10_000,
      discount_cents: 0,
      net_cents: 10_000,
      vat_cents: 0,
      total_cents: 10_000,
      advance_cents: 0,
      balance_cents: 10_000,
    },
  };
  const pdf = () =>
    Promise.resolve(
      new Response(new Blob(["%PDF-1.7"], { type: "application/pdf" }), {
        status: 200,
        headers: { "Content-Type": "application/pdf", "Content-Disposition": 'attachment; filename="ponuda-2026-0007-v1.pdf"' },
      }),
    );
  const noPdf = () => json(503, { title: "PDFs are not available", status: 503, detail: "PDFs cannot be made on this server" });

  function api(document: () => Promise<Response>) {
    return vi.fn((url: string) => {
      if (url.endsWith("/auth/me")) return json(200, owner);
      if (url.endsWith("/calculate")) return json(200, calculation);
      if (url.includes(".pdf")) return document();
      if (url.endsWith("/status")) return json(200, { ...quote, status: "sent" });
      if (url.endsWith("/quotes/q1")) return json(200, quote);
      if (url.includes("/price-lists/")) return json(200, { id: "p", status: "published", entries: [] });
      return json(200, []);
    });
  }

  function onNavigator(name: "share" | "canShare", value: unknown) {
    Object.defineProperty(navigator, name, { value, configurable: true, writable: true });
  }

  // File names of the downloads the screen started.
  const downloads: string[] = [];
  beforeEach(() => {
    downloads.length = 0;
    Object.defineProperty(URL, "createObjectURL", { value: vi.fn(() => "blob:pdf"), configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloads.push(this.download);
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    onNavigator("share", undefined);
    onNavigator("canShare", undefined);
  });

  /** "Send to client", once the price is there (it is disabled until then). */
  async function sendButton(): Promise<HTMLButtonElement> {
    const button = await screen.findByRole<HTMLButtonElement>("button", { name: /Pošalji klijentu/ });
    await waitFor(() => expect(button.disabled).toBe(false));
    return button;
  }

  it("downloads the client PDF in the language picked for the client", async () => {
    const fetch = api(pdf);
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />, "/quotes/q1"));

    fireEvent.click(await screen.findByRole("radio", { name: "English" }));
    fireEvent.click(screen.getByRole("button", { name: /Ponuda za klijenta \(PDF\)/ }));

    await waitFor(() => expect(downloads).toEqual(["ponuda-2026-0007-v1.pdf"]));
    expect(fetch.mock.calls.some(([url]) => url.endsWith("/quotes/q1/revisions/1/quote.pdf?lang=en"))).toBe(true);
  });

  it("sends the PDF through the share sheet and marks the draft sent", async () => {
    const share = vi.fn(() => Promise.resolve());
    onNavigator("canShare", () => true);
    onNavigator("share", share);
    const fetch = api(pdf);
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />, "/quotes/q1"));

    fireEvent.click(await sendButton());

    await waitFor(() => expect(share).toHaveBeenCalled());
    const [data] = share.mock.calls[0] as unknown as [{ files: File[] }];
    expect(data.files[0]?.name).toBe("ponuda-2026-0007-v1.pdf");
    expect(fetch.mock.calls.some(([url]) => url.endsWith("/quote.pdf?lang=bs"))).toBe(true);
    await waitFor(() => expect(fetch.mock.calls.some(([url]) => url.endsWith("/quotes/q1/status"))).toBe(true));
  });

  it("does not mark the quote sent when he closes the share sheet", async () => {
    onNavigator("canShare", () => true);
    onNavigator("share", vi.fn(() => Promise.reject(new DOMException("closed", "AbortError"))));
    const fetch = api(pdf);
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />, "/quotes/q1"));

    fireEvent.click(await sendButton());

    await waitFor(() => expect(fetch.mock.calls.some(([url]) => url.includes(".pdf"))).toBe(true));
    await act(() => Promise.resolve());
    expect(fetch.mock.calls.some(([url]) => url.endsWith("/status"))).toBe(false);
  });

  it("opens the total into its layers", async () => {
    vi.stubGlobal("fetch", api(pdf));
    render(wrap(<App />, "/quotes/q1"));

    fireEvent.click(await screen.findByRole("button", { name: "Od čega se sastoji?" }));

    const layers = screen.getByText("Ostatak").closest("dl");
    expect(layers?.textContent).toContain("100,00 €");
    expect(screen.getByRole("button", { name: "Sakrij" })).toBeTruthy();
  });

  it("locks an accepted quote: no sending, no editing", async () => {
    const accepted = { ...quote, status: "accepted", accepted_at: "2026-11-18T10:00:00Z" };
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("/quotes/q1")) return json(200, accepted);
        if (url.endsWith("/payments")) return json(200, []);
        return api(pdf)(url);
      }),
    );
    render(wrap(<App />, "/quotes/q1"));

    expect(await screen.findByText("Prihvaćena ponuda se više ne mijenja.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Pošalji klijentu/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /Dodaj prozor/ })).toBeNull();
  });

  it("sends the summary as text when no PDF can be made, and says so", async () => {
    const share = vi.fn(() => Promise.resolve());
    onNavigator("share", share);
    vi.stubGlobal("fetch", api(noPdf));
    render(wrap(<App />, "/quotes/q1"));

    fireEvent.click(await sendButton());

    await waitFor(() => expect(share).toHaveBeenCalled());
    const [data] = share.mock.calls[0] as unknown as [{ text: string; files?: File[] }];
    expect(data.files).toBeUndefined();
    expect(data.text).toContain("2026-0007");
    expect(await screen.findByText(/Ovaj put bez PDF-a \(PDFs cannot be made on this server\)/)).toBeTruthy();
  });
});
