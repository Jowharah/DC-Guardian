/**
 * Browser tests for the human-review flows operators use most:
 * Evidence verdicts, unified group review, and Decision re-evaluation.
 * The API is mocked (see mockApi.ts); the UI is the real built dashboard.
 */
import {expect, test} from "@playwright/test";
import {GROUP_ID, PPE_ID, SSH_ID, installMockApi, signIn} from "./mockApi";

test("sign-in shows the Monitoring Center", async ({page}) => {
  await installMockApi(page);
  await signIn(page);
  await expect(page.getByRole("button", {name: /Monitoring Center/}).first()).toBeVisible();
  await expect(page.getByText(PPE_ID).first()).toBeVisible();
});

test("operator overrides a PPE result and it shows as human verified", async ({page}) => {
  const state = await installMockApi(page);
  await signIn(page);
  await page.getByRole("button", {name: /Human Review Queue/}).click();

  const item = page.locator("article.reviewRecord", {hasText: PPE_ID});
  await item.getByRole("button", {name: "Review Evidence & record verdict"}).click();
  await page.locator("#evidenceVerdict").selectOption("OVERRIDDEN");
  await page.locator("#evidenceCorrected").selectOption("COMPLIANT");
  await page.locator("#evidenceRationale").fill("Vest visible under the jacket; detector missed it.");
  const record = page.getByRole("button", {name: "Record verdict", exact: true});
  await expect(record).toBeDisabled();
  await page.getByText("I confirm this is my own review of this Evidence.").click();
  await record.click();

  await expect(page.getByText("Verdict recorded in the audit chain")).toBeVisible();
  await expect(page.getByText("Overridden → Compliant")).toBeVisible();
  const post = state.requests.find(r => r.method === "POST" && r.path === `/api/v1/evidence-reviews/ppe/${PPE_ID}`);
  expect(post?.body).toMatchObject({verdict: "OVERRIDDEN", corrected_status: "COMPLIANT", acknowledgment: true});

  // The queue and Monitoring Center reflect the override; the detector result stays visible.
  await expect(item.getByText("HUMAN OVERRIDDEN")).toBeVisible({timeout: 10_000});
  await page.getByRole("button", {name: /Monitoring Center/}).first().click();
  await expect(page.getByText("COMPLIANT · HUMAN VERIFIED")).toBeVisible({timeout: 10_000});
});

test("override must name a different status and needs a rationale", async ({page}) => {
  await installMockApi(page);
  await signIn(page);
  await page.getByRole("button", {name: /Human Review Queue/}).click();
  await page.locator("article.reviewRecord", {hasText: PPE_ID}).getByRole("button", {name: "Review Evidence & record verdict"}).click();
  await page.locator("#evidenceVerdict").selectOption("OVERRIDDEN");
  // The detector's own status is not offered as an override.
  await expect(page.locator("#evidenceCorrected option", {hasText: "Non-compliant"})).toHaveCount(0);
  await page.locator("#evidenceCorrected").selectOption("COMPLIANT");
  await page.getByText("I confirm this is my own review of this Evidence.").click();
  await page.locator("#evidenceRationale").fill("too short");
  await expect(page.getByRole("button", {name: "Record verdict", exact: true})).toBeDisabled();
});

test("group review requires a consented specialist evaluation first", async ({page}) => {
  const state = await installMockApi(page);
  await signIn(page);
  await page.getByRole("button", {name: /Human Review Queue/}).click();
  await page.locator("article.reviewRecord", {hasText: GROUP_ID}).getByRole("button", {name: "Open review & audit history"}).click();

  const run = page.getByRole("button", {name: "Run specialist evaluation"});
  await expect(run).toBeDisabled();
  await page.getByText("I authorize sending this group's filtered Evidence to OpenAI").click();
  await run.click();
  await expect(page.getByText("Specialist evaluation saved")).toBeVisible();
  expect(state.requests.some(r => r.method === "POST" && r.path.endsWith(`${GROUP_ID}/specialists`))).toBe(true);

  // Once the review requirement loads (queue polls every 5 s), recording unlocks.
  await expect(page.locator("#humanReviewOutcome")).toBeEnabled({timeout: 12_000});
  await page.locator("#humanReviewOutcome").selectOption("NEEDS_FOLLOW_UP");
  await page.locator("#humanReviewRationale").fill("Group needs on-site follow-up by the safety team.");
  await page.getByText("I confirm this is my human review of the selected Evidence.").click();
  await page.getByRole("button", {name: "Record human review"}).click();
  await expect(page.getByText("Review recorded in the local audit history.")).toBeVisible();
  expect(state.groupReviews).toHaveLength(1);
});

test("a cleared input flags the Decision and re-evaluation removes its severity", async ({page}) => {
  const state = await installMockApi(page);
  state.sshInputOverridden = true;
  await signIn(page);

  const row = page.locator("button.feedRow", {hasText: SSH_ID});
  await expect(row.getByText("⚠ RE-EVALUATE")).toBeVisible();
  await row.click();
  await expect(page.getByText("Human verdict changed a Decision input")).toBeVisible();
  await page.getByRole("button", {name: "Re-evaluate with human-verified inputs"}).click();

  await expect(page.getByText(/Re-evaluated .* on human-verified inputs/)).toBeVisible();
  await expect(page.getByText("original detector-based severity:")).toBeVisible();
  expect(state.requests.some(r => r.method === "POST" && r.path === `/api/v1/decisions/ssh/${SSH_ID}/reevaluate`)).toBe(true);
});

test("analytics shows detector outcomes per domain with human verdicts beside them", async ({page}) => {
  await installMockApi(page);
  await signIn(page);
  await page.getByRole("button", {name: /Analytics Dashboard/}).click();
  const panel = page.locator("section", {has: page.getByRole("heading", {name: "Detector outcomes by domain"})});
  const ppe = panel.locator(".analyticsOutcome", {hasText: "Safety / PPE"});
  await expect(ppe).toContainText("1 records · 1 abnormal (100%)");
  await ppe.getByRole("button", {name: /NON COMPLIANT/}).click();
  await expect(page.getByText(PPE_ID).first()).toBeVisible();
  await expect(page.getByText("No human verdict").first()).toBeVisible();
});

test("monitoring summary counts what needs attention and filters the feed", async ({page}) => {
  await installMockApi(page);
  await signIn(page);
  await expect(page.getByRole("status").filter({hasText: /Live · updated/})).toBeVisible();
  // Mock: PPE non-compliant, Face recognized, SSH anomaly (all without verdicts); one group not yet evaluated.
  const attention = page.locator(".summaryCard", {hasText: "Needs attention"});
  await expect(attention).toContainText("1 group not evaluated");
  await expect(page.locator(".summaryCard", {hasText: "Correlations"})).toContainText("1 group");
  await expect(page.getByText("Operating mode")).toHaveCount(0);

  await attention.click();
  await expect(page.getByText("Showing:")).toContainText("Items needing attention");
  await expect(page.locator("button.feedRow", {hasText: "Unified correlation"})).toBeVisible();
  await page.getByRole("button", {name: "Show all"}).click();
  await expect(page.getByText("Showing:")).toHaveCount(0);

  await page.locator(".domainChip", {hasText: "Maintenance"}).click();
  await expect(page.locator("button.feedRow", {hasText: "Unified correlation"})).toHaveCount(0);
});

test("v2 Decisions show on single events and groups, and the severity filter uses them", async ({page}) => {
  await installMockApi(page);
  await signIn(page);
  const ppeRow = page.locator("button.feedRow", {hasText: PPE_ID});
  await expect(ppeRow.locator(".severity-low")).toHaveText("LOW");
  await expect(page.locator("button.feedRow", {hasText: "Unified correlation"})).toContainText("HIGH · LINKED");
  await expect(page.locator(".summaryCard", {hasText: "Decisions"}).last()).toContainText("HIGH 1");

  await page.getByLabel("Filter incidents").selectOption("LOW");
  await expect(ppeRow).toBeVisible();
  await expect(page.locator("button.feedRow", {hasText: "Unified correlation"})).toHaveCount(0);
  await page.getByLabel("Filter incidents").selectOption("ALL");

  await page.locator("button.feedRow", {hasText: "Unified correlation"}).click();
  await expect(page.getByText("Group Decision · DCG-DECISION-v2")).toBeVisible();
  await expect(page.getByText(/Unified Decision: HIGH · DCG-DECISION-v2 · validated on author labels/)).toBeVisible();
});
