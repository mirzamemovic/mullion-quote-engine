import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../i18n";
import { setLanguage } from "../i18n";
import { App } from "../App";
import { emptyReadings, type Readings } from "../lib/readings";
import { MeasureStep } from "./position/MeasureStep";

function wrap(children: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

function json(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

beforeEach(() => setLanguage("bs"));
afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("asks a visitor to log in", async () => {
    vi.stubGlobal("fetch", vi.fn(() => json(401, { title: "log in first", status: 401 })));
    render(wrap(<App />));

    expect(await screen.findByRole("heading", { name: "Prijava" })).toBeInTheDocument();
    expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prijavi se" })).toBeInTheDocument();
  });

  it("says plainly when the login is wrong", async () => {
    const fetch = vi.fn((url: string) =>
      url.endsWith("/auth/me") ? json(401, {}) : json(401, { title: "login failed", detail: "wrong email or password", status: 401 }),
    );
    vi.stubGlobal("fetch", fetch);
    render(wrap(<App />));
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
