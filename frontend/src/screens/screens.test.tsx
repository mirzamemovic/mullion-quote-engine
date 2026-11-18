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
