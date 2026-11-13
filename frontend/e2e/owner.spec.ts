/**
 * The owner's day on the demo workshop: log in, new quote, measure two windows, see the total,
 * with no serious accessibility issue on the main screens. Needs the running stack and a seeded
 * demo (see playwright.config.ts); the demo data is invented.
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const EMAIL = process.env.E2E_EMAIL ?? "demo@example.invalid";
const PASSWORD = process.env.E2E_PASSWORD ?? "";

async function noSeriousA11yIssues(page: Page, screen: string) {
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const serious = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious, `${screen}: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
}

async function measureWindow(page: Page, widths: string[], heights: string[], type: RegExp) {
  const labels = ["Širina gore", "Širina sredina", "Širina dolje", "Visina lijevo", "Visina sredina", "Visina desno"];
  for (const [i, value] of [...widths, ...heights].entries()) {
    await page.getByLabel(labels[i] ?? "").fill(value);
  }
  await expect(page.getByRole("button", { name: "Kako je izračunato?" })).toBeVisible();
  await page.getByRole("button", { name: /Dalje: tip prozora/ }).click();
  await page.getByRole("button", { name: type }).click();
  await page.getByRole("button", { name: "Spremi prozor" }).click();
  await expect(page.getByText("Ukupno za klijenta")).toBeVisible();
}

test("log in, measure two windows, see the total", async ({ page }) => {
  test.skip(!PASSWORD, "set E2E_PASSWORD to the demo password printed by seed-demo");

  await page.goto("/");
  await noSeriousA11yIssues(page, "login");
  await page.getByLabel("E-mail").fill(EMAIL);
  await page.getByLabel("Lozinka").fill(PASSWORD);
  await page.getByRole("button", { name: "Prijavi se" }).click();
  await expect(page.getByRole("note")).toContainText("DEMO");
  await noSeriousA11yIssues(page, "quotes");

  await page.getByRole("link", { name: /Nova ponuda/ }).click();
  await page.getByRole("button", { name: /Probni klijent/ }).click();
  await noSeriousA11yIssues(page, "new quote");
  await page.getByRole("button", { name: "Napravi ponudu" }).click();

  await expect(page.getByLabel("Širina gore")).toBeVisible();
  await noSeriousA11yIssues(page, "measure");
  await measureWindow(page, ["1032", "1030", "1031"], ["1240", "1238", "1241"], /Jedno krilo/);

  await page.getByRole("link", { name: /Dodaj prozor/ }).click();
  await measureWindow(page, ["1452", "1450", "1449"], ["1440", "1441", "1439"], /Dva polja sa stubom/);

  const total = page.locator("#total ~ p");
  await expect(total).toContainText("€");
  await expect(total).not.toHaveText("–");
  await noSeriousA11yIssues(page, "summary");
});
