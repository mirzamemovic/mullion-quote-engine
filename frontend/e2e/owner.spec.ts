/**
 * A visitor's first minutes, end to end against the real stack: "Try it" opens a private sample
 * workshop (no password needed), a new quote, two measured windows, a sill, the total changing,
 * and the setup checklist, with no serious accessibility issue on the main screens. The sample
 * data is invented.
 */
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

async function noSeriousA11yIssues(page: Page, screen: string) {
  const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  const serious = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(serious, `${screen}: ${serious.map((v) => v.id).join(", ")}`).toEqual([]);
}

async function measureWindow(page: Page, widths: string[], heights: string[], type: RegExp) {
  const labels = ["Width top", "Width middle", "Width bottom", "Height left", "Height middle", "Height right"];
  for (const [i, value] of [...widths, ...heights].entries()) {
    await page.getByLabel(labels[i] ?? "", { exact: true }).fill(value);
  }
  await expect(page.getByRole("button", { name: "How was this worked out?" })).toBeVisible();
  await page.getByRole("button", { name: /Next: window type/ }).click();
  await page.getByRole("button", { name: type }).click();
  await page.getByRole("button", { name: "Save window" }).click();
  await expect(page.getByText("Total for the client")).toBeVisible();
}

const total = (page: Page) => page.locator("#total").locator("xpath=../following-sibling::p");

test("try it, quote two windows and a sill, see the total follow", async ({ page }) => {
  await page.goto("/");
  await noSeriousA11yIssues(page, "landing");
  await page.getByRole("button", { name: "Try it with sample data" }).click();
  await expect(page.getByRole("note")).toContainText("don't enter real client data");
  await noSeriousA11yIssues(page, "quotes");

  await page.getByRole("link", { name: /New quote/ }).click();
  await page.getByRole("button", { name: /Sample client/ }).click();
  await page.getByText(/Euro-Design 70/).click();
  await noSeriousA11yIssues(page, "new quote");
  await page.getByRole("button", { name: "Create quote" }).click();

  await expect(page.getByLabel("Width top", { exact: true })).toBeVisible();
  await noSeriousA11yIssues(page, "measure");
  await measureWindow(page, ["1032", "1030", "1031"], ["1240", "1238", "1241"], /Single sash/);
  await page.getByRole("link", { name: /Add window/ }).click();
  await measureWindow(page, ["1452", "1450", "1449"], ["1440", "1441", "1439"], /Two fields/);
  await expect(total(page)).toContainText("€");
  const before = await total(page).innerText();
  await noSeriousA11yIssues(page, "summary");

  await page.getByRole("button", { name: "Add an extra" }).click();
  await page.getByLabel("Length (mm)").fill("1000");
  await page.getByRole("button", { name: "Add an extra" }).click();
  await expect(page.getByText(/Sill · PVC \d+ mm/)).toBeVisible();
  await expect(total(page)).not.toHaveText(before);

  await page.goto("/workshop/setup");
  await expect(page.getByText("Ready to quote.")).toBeVisible();
  await noSeriousA11yIssues(page, "setup checklist");
});
