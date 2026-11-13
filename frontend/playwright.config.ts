/**
 * End-to-end tests against the real stack (PLAN.md section 10): `docker compose up`, then
 * `docker compose exec app /app/.venv/bin/python -m quote_engine.manage seed-demo` and
 * `E2E_PASSWORD=<printed password> npm run e2e`. Pixel 7 profile, axe on the main screens.
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
