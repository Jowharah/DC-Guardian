/**
 * Automated WCAG 2.1 A/AA checks (axe-core) on every main screen, with the
 * mocked API. Any violation fails the test and is listed with its element.
 * Automated scans catch roughly a third of accessibility issues; keyboard use
 * and screen-reader wording still need manual review.
 */
import {expect, test, type Page} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {PPE_ID, installMockApi, signIn} from "./mockApi";

async function violations(page: Page) {
  const result = await new AxeBuilder({page}).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  return result.violations.flatMap(v => v.nodes.map(n => `${v.id} (${v.impact}): ${n.target.join(" ")}`));
}

test("sign-in screen has no WCAG A/AA violations", async ({page}) => {
  await installMockApi(page);
  await page.goto("/");
  expect(await violations(page)).toEqual([]);
});

test("every main screen has no WCAG A/AA violations", async ({page}) => {
  await installMockApi(page);
  await signIn(page);
  const found: string[] = [];
  await expect(page.getByText("Live · updated").first()).toBeVisible();
  found.push(...(await violations(page)).map(v => "monitoring: " + v));
  await page.locator("button.feedRow", {hasText: "Correlated group"}).click();
  await expect(page.getByText(/Rule-based Decision ·/)).toBeVisible();
  found.push(...(await violations(page)).map(v => "group detail: " + v));
  await page.locator("button.feedRow", {hasText: PPE_ID}).click();
  await expect(page.getByRole("region", {name: "Single-event specialist evaluation"})).toBeVisible();
  found.push(...(await violations(page)).map(v => "PPE detail: " + v));
  for (const [nav, name] of [[/Analytics Dashboard/, "analytics"], [/Human Review Queue/, "review queue"], [/Scenario Lab/, "scenario lab"]] as const) {
    await page.getByRole("button", {name: nav}).click();
    await page.waitForTimeout(500);
    found.push(...(await violations(page)).map(v => name + ": " + v));
  }
  expect(found).toEqual([]);
});
