/**
 * Keyboard-only use: sign in, reach an event in the feed with Tab, open it with
 * Enter, and see a visible focus indicator on every step. Complements the axe
 * scan, which does not test keyboard operation.
 */
import {expect, test, type Page} from "@playwright/test";
import {PPE_ID, installMockApi} from "./mockApi";

async function focusedOutline(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return null;
    const style = getComputedStyle(el);
    return {tag: el.tagName, outline: style.outlineStyle !== "none" && style.outlineWidth !== "0px",
            filter: style.filter !== "none"};
  });
}

async function tabTo(page: Page, matches: () => Promise<boolean>, limit = 80) {
  for (let i = 0; i < limit; i++) {
    await page.keyboard.press("Tab");
    if (await matches()) return true;
  }
  return false;
}

test("the dashboard can be used with the keyboard alone", async ({page}) => {
  await installMockApi(page);
  await page.goto("/");
  await page.keyboard.press("Tab");
  await page.keyboard.type("test-operator");
  await page.keyboard.press("Tab");
  await page.keyboard.type("test-password");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", {name: /Monitoring Center/}).first()).toBeVisible();

  const reached = await tabTo(page, async () =>
    (await page.evaluate(() => document.activeElement?.textContent ?? "")).includes(PPE_ID));
  expect(reached, "PPE row reachable with Tab").toBe(true);
  const focus = await focusedOutline(page);
  expect(focus?.outline || focus?.filter, "visible focus on the feed row").toBe(true);

  await page.keyboard.press("Enter");
  await expect(page.getByRole("region", {name: "Investigation state"})).toBeVisible();

  const control = await tabTo(page, async () =>
    (await page.evaluate(() => document.activeElement?.closest("[aria-label='Investigation state']") !== null)));
  expect(control, "investigation controls reachable with Tab").toBe(true);
  expect((await focusedOutline(page))?.outline, "visible focus on the investigation control").toBe(true);
});
