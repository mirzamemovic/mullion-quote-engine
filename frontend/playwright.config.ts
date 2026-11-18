/**
 * End-to-end tests against the real stack (PLAN.md section 10): `docker compose up` (or the
 * backend and `npm run dev`, with `E2E_BASE_URL=http://localhost:5173`), then `npm run e2e`.
 * The test opens its own "Try it" sandbox, so no password is needed. Pixel 7 profile, axe on the
 * main screens.
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8000",
    trace: "retain-on-failure",
  },
  projects: [{ name: "pixel-7", use: { ...devices["Pixel 7"] } }],
});
