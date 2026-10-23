/**
 * Changes made in response to the usability study (2026-10-21/22, three participants).
 * Each test names the finding it covers. The API is mocked (see mockApi.ts).
 */
import {expect, test} from "@playwright/test";
import {PPE_ID, SSH_ID, installMockApi, signIn} from "./mockApi";

test("a group states first why it was grouped, that it is not proof of cause, and that rules set severity", async ({page}) => {
  // Finding: no participant found the causation statement (T3); none knew rules set severity (Q2).
  await installMockApi(page);
  await signIn(page);
  await page.locator("button.feedRow", {hasText: "Correlated group"}).click();
  const glance = page.getByRole("region", {name: "Group at a glance"});
  await expect(glance).toContainText("ZONE-B, 4 min apart");
  await expect(glance).toContainText("Not proof of cause.");
  await expect(glance).toContainText("set by fixed rules (DCG-DECISION-v2), not by AI");
  await expect(glance.locator(".domainTag")).toHaveText(["Cybersecurity", "Physical security", "Safety / PPE"]);
  // The long explanations are folded away until asked for.
  await expect(page.getByText("What the graph shows, and what it does not")).toBeVisible();
  await expect(page.getByText(/Selected mapped Evidence and existing infrastructure relationships/)).toBeHidden();
});

test("domain counts say what they count", async ({page}) => {
  // Finding: "2/2" in the domain strip confused all three participants (T1).
  await installMockApi(page);
  await signIn(page);
  await expect(page.locator(".domainChip", {hasText: "Cybersecurity"})).toContainText(/\d+ abnormal of \d+/);
  await expect(page.getByText(/not yet confirmed by a human/).first()).toBeVisible();
});

test("single events show that they are not reviewed yet", async ({page}) => {
  // Finding: groups showed a review state, single events did not (P02).
  await installMockApi(page);
  await signIn(page);
  await expect(page.locator("button.feedRow", {hasText: SSH_ID}).getByText("NOT REVIEWED")).toBeVisible();
});

test("a verdict can be recorded from inside a group and shows as saved", async ({page}) => {
  // Finding: inside a group the verdict form was missing, so P03 had to go to the Review Queue;
  // P02 could not tell that a verdict had been saved.
  const state = await installMockApi(page);
  await signIn(page);
  await page.locator("button.feedRow", {hasText: "Correlated group"}).click();
  await page.locator("summary", {hasText: `Record verdict · ${PPE_ID}`}).click();
  await expect(page.getByText("Not reviewed yet.").first()).toBeVisible();
  await page.locator("#evidenceRationale").fill("Checked the image: vest not visible, detector result confirmed.");
  await page.getByText("I confirm this is my own review of this Evidence.").click();
  await page.getByRole("button", {name: "Record verdict", exact: true}).click();
  await expect(page.getByText(/Verdict saved/)).toBeVisible();
  expect(state.verdicts.some(v => v.kind === "ppe" && v.evidence_id === PPE_ID)).toBe(true);
});

test("a non-compliant PPE result explains that it means not detected", async ({page}) => {
  // Finding: two of three participants read non-compliant as proof the equipment was missing (Q5).
  await installMockApi(page);
  await signIn(page);
  await page.locator("button.feedRow", {hasText: PPE_ID}).click();
  await expect(page.getByText(/was not detected for at least one person/)).toBeVisible();
});

test("the logo returns to the Monitoring Center", async ({page}) => {
  // Finding: P03 expected the logo to go to the home page.
  await installMockApi(page);
  await signIn(page);
  await page.getByRole("button", {name: /Analytics Dashboard/}).click();
  await page.getByRole("button", {name: "DC-GUARDIAN home: Monitoring Center"}).click();
  await expect(page.getByRole("heading", {name: "Security & operations overview"})).toBeVisible();
});

test("the review queue has three status tabs and tags each item with its detailed state", async ({page}) => {
  // Finding: eleven category tabs were too many (P01, P03); filter by event type (P02).
  await installMockApi(page);
  await signIn(page);
  await page.getByRole("button", {name: /Human Review Queue/}).click();
  await expect(page.getByRole("tab")).toHaveText([/To do/, /In progress/, /Completed/, /All/]);
  await expect(page.getByRole("tab", {name: /To do/})).toHaveAttribute("aria-selected", "true");
  const ppe = page.locator("article.reviewRecord", {hasText: PPE_ID});
  await expect(ppe.locator(".statusTag")).toHaveText("Not reviewed");
  await page.getByLabel("Filter by event type").selectOption("SSH");
  await expect(ppe).toHaveCount(0);
  await expect(page.locator("article.reviewRecord", {hasText: SSH_ID}).first()).toBeVisible();
});

test("feed and analytics can be limited to calendar dates", async ({page}) => {
  // Finding: P01 wanted to choose days, not only fixed periods; filter by zone (P01).
  await installMockApi(page);
  await signIn(page);
  const rows = page.locator("button.feedRow");
  await expect(rows.first()).toBeVisible();
  await page.getByRole("group", {name: "Received date range"}).getByLabel(/from/).fill("2000-01-01");
  await page.getByRole("group", {name: "Received date range"}).getByLabel(/^to/).fill("2000-01-02");
  await expect(rows).toHaveCount(0);
  await page.getByRole("button", {name: "Clear dates"}).click();
  await expect(rows.first()).toBeVisible();
  await expect(page.getByLabel("Filter by zone")).toBeVisible();
  await page.getByRole("button", {name: /Analytics Dashboard/}).click();
  await expect(page.getByRole("group", {name: "Custom dates: date range"})).toBeVisible();
});
