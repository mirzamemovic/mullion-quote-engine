/**
 * The README screenshots, taken from the running app in a "Try it" sandbox (invented sample
 * data, never a real client or price). Off by default; with the stack running:
 *   SCREENSHOTS=1 npx playwright test screenshots
 * The pictures go to docs/screenshots/.
 */
import { fileURLToPath } from "node:url";

import { expect, test, type Page } from "@playwright/test";

const OUT = fileURLToPath(new URL("../../docs/screenshots/", import.meta.url));

test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to refresh the README screenshots");
test.use({ deviceScaleFactor: 2 });

const shot = (page: Page, name: string) => page.screenshot({ path: `${OUT}${name}.png` });

async function readings(page: Page, widths: string[], heights: string[]) {
  const labels = ["Width top", "Width middle", "Width bottom", "Height left", "Height middle", "Height right"];
  for (const [i, value] of [...widths, ...heights].entries()) {
    await page.getByLabel(labels[i] ?? "", { exact: true }).fill(value);
  }
  await expect(page.getByRole("button", { name: "How was this worked out?" })).toBeVisible();
}

async function saveAs(page: Page, type: RegExp) {
  await page.getByRole("button", { name: /Next: window type/ }).click();
  await page.getByRole("button", { name: type }).click();
  await page.getByRole("button", { name: "Save window" }).click();
  await expect(page.getByText("Total for the client")).toBeVisible();
}

test("README screenshots", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Try it with sample data" })).toBeVisible();
  await shot(page, "01-landing");

  await page.getByRole("button", { name: "Try it with sample data" }).click();
  await page.getByRole("link", { name: /New quote/ }).click();
  await page.getByRole("button", { name: /Sample client/ }).click();
  await page.getByText(/Euro-Design 70/).click();
  await page.getByRole("button", { name: "Create quote" }).click();

  // Six readings; the smallest of each dimension counts, minus the installation gap.
  await readings(page, ["1032", "1030", "1031"], ["1240", "1238", "1241"]);
  await page.getByRole("button", { name: "How was this worked out?" }).click();
  await shot(page, "02-measure");

  await page.getByRole("button", { name: /Next: window type/ }).click();
  await expect(page.getByRole("button", { name: /Single sash/ })).toBeVisible();
  await shot(page, "03-window-type");
  await page.getByRole("button", { name: /Single sash/ }).click();
  await page.getByRole("button", { name: "Save window" }).click();
  await expect(page.getByText("Total for the client")).toBeVisible();

  await page.getByRole("link", { name: /Add window/ }).click();
  await readings(page, ["1452", "1450", "1449"], ["1440", "1441", "1439"]);
  await saveAs(page, /Two fields/);

  const plan = page.getByRole("button", { name: /Cutting plan/ });
  await plan.click();
  // The plan's heading just under the sticky top bar, so the first bars show in full.
  await plan.evaluate((button) => {
    window.scrollTo(0, button.getBoundingClientRect().top + window.scrollY - 84);
  });
  await shot(page, "05-cutting-plan");

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole("button", { name: "What is in it?" }).click();
  await shot(page, "04-quote-total");

  await page.goto("/workshop/setup");
  await expect(page.getByText("Ready to quote.")).toBeVisible();
  await shot(page, "06-setup-checklist");
});
