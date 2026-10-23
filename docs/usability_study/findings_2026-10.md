# Usability study: findings and changes (October 2026)

Three participants from outside the project team took part on 21–22 October 2026, after a pilot on 20 October. All saw the same freshly prepared study data. Scores come from `results.csv` via `usability_score.py` (see [`results_summary.md`](results_summary.md)). Session notes and questionnaire sheets stay with the team; this file uses participant codes only.

## Participants

| Code | Background | Dashboard experience | Session |
|---|---|---|---|
| P01 | Cybersecurity | Regularly | AI Investigator (T8) and PPE upload (T9) with help |
| P02 | IT operations or support | Never | T2, T8 and T9 with help |
| P03 | Data science | Regularly | Optional tasks not attempted |

**Caveats:**
- **Sample size:** three participants is a formative sample. It finds the main problems, but its numbers are not representative.
- **P01's questionnaire:** P01 answered in sentences rather than on the 1–5 scales. The project team coded each sentence to the nearest value (the reasons are kept with the session notes), so P01's SUS is researcher-coded.
- **Timing and help:**
  - Some tasks were done together, so they have one shared time and no per-task times.
  - Facilitator help is recorded per task and caps a task at 0.5.
  - Ease ratings (SEQ) were not collected.

## Results

| Measure | Result |
|---|---|
| Core tasks (T1–T7) | T1, T4, T5, T6, T7: 100% success; T2: 83% (one with help); **T3: 50%**, the slowest task (median 255 s) |
| System Usability Scale | P01 55.0 (coded), P02 87.5, P03 40.0; **mean 60.8** (63.8 without P01). About 68 is the cross-study average |
| Concept check (6 statements about what the system claims) | **Mean 2.3 of 6** correct |
| Severity comes from fixed rules (Q2) | **0 of 3** correct |
| "Non-compliant" proves the PPE was missing (Q5, false) | 1 of 3 correct |
| A verdict overwrites the detector result (Q3, false) | 1 of 3 correct |
| Trust (1–5) | Would use it to prioritise **4.3**; would let it decide without checking **2.0** (low is desired); understood why an alert had its severity **2.7** |

**What the results show:**
- **Tasks versus concepts:** participants could do the operator's tasks, but did not take in how the system reasons.
- **The safeguards were on screen but not noticed.** The statements that grouping is not proof of cause, that fixed rules set severity, and that "non-compliant" means "not detected" were all present. In T3 every participant missed the causation statement; all three said the screens carry too much text.
- **Trust:** participants would use the system to decide what to look at first, but not to decide for them. That is the intended balance.

## Problems found and what changed

The changes are display-only: detector outputs, correlation rules, Decision rules and severity are unchanged. **They were made after the sessions and have not been re-tested with participants.**

| Finding | Raised by | Change |
|---|---|---|
| Missed that grouping is not proof of cause (T3); thought AI sets severity (Q2) | All | **"At a glance" box** at the top of every group: why grouped (zone, minutes apart, links), **"Not proof of cause"**, severity "set by **fixed rules**, **not by AI**", human-review status |
| Too much text in the group detail | All | Long explanations (how severity is decided, what the graph shows) folded into expandable sections |
| "2/2" domain counts unclear (T1) | All | "2 abnormal of 3", with "Abnormal = detector output, not yet confirmed by a human" |
| "Group", "member", "active concern" and "Decision" unclear; inconsistent wording | P01, P03 | "Correlated group"; "Events in this group"; "Counts toward severity" or "Context only · not counted"; "Rule-based Decision(s)"; plain domain names |
| Single events showed no review state; no clear "saved" state after a verdict | P02 | **NOT REVIEWED** badge on unreviewed events; verdict state shown as a coloured box; "✓ Verdict saved" confirmation |
| No verdict form for an event opened inside a group; had to leave for the Review Queue | P03 | **Record verdict** on each event inside the group |
| Read "non-compliant" as proof the PPE was missing (Q5) | P01, P02 | Note on non-compliant PPE results: a required item was **not detected**, which does not prove it was missing |
| Wanted colour coding by event type | P03 | Feed rows and domain counts colour-coded by domain; domain tags in the group summary |
| Expected the logo to go home | P03 | Logo returns to the Monitoring Center |
| Too many Review Queue tabs; wanted completed / not completed / assigned, with outcomes as tags | P01, P03 | Three status tabs, **To do / In progress / Completed** (plus All); the detailed state (for example "Human override", "Group review needed") is a coloured tag on each item; "Inconclusive" counts as in progress, not done |
| Wanted to filter by event type | P02 | Type filter in the Review Queue |
| Wanted to choose days, not only 24 h / 7 days; filter by zone | P01 | Calendar date range (from / to) on the Monitoring Center feed and in Analytics; zone filter on the feed |
| Inconsistent capitalisation in titles | P03 | Headings no longer forced into Title Case; each reads as written |
| Neo4j graph unclear; wanted the zone highlighted | P01 | The zone node is highlighted in amber with a legend note; crowded graphs stagger columns so nodes no longer overlap |
| Text too small on a laptop | P02 | Feed rows, domain counts and summary-card details one size larger |
| Wanted a short summary before the detail | P01 | "At a glance" summary for single events too: result, what it means, review state, who decides |
| Wanted a short guide to the terms | P03 | "How to read this screen" panel on the Monitoring Center (collapsed by default) |
| Wanted clearer explanation of AI output versus verdicts | P03 | A "Who says what" note in every AI panel: the detector produced it, the AI only explains, fixed rules set severity, the human verdict counts |
| Wanted a simpler main view with detail on demand | P03 | Groups open in a **Simple view** (summary, Decision, events and verdicts, investigation state); **Full detail** adds the graph, timeline, AI analysis and source links. The group-severity caveat stays visible in both |
| SOAR-style status charts (completed, pending) | Facilitator | "Review progress" chart in Analytics: completed / in progress / to do per domain and for groups |

Browser tests cover each change (`presentation/frontend/e2e/usability-findings.spec.ts`).

## Not done (future work)

- **Work management:** assignment and team workload, and auto-assignment by role (P01, P02).
- **Filters:** by user or team (needs assignment first).
- **Onboarding:** an interactive first-time tour (P03). The help panel and the simple view cover part of this.
- **Recommended next study:** repeat the concept check (Q1–Q6) and T3 with new participants, to measure whether the changes help.

## Domain remark

P03 noted that cyber and physical alerts are usually handled separately, and that most attacks are remote. A physical–cyber link matters mainly for insider threats, which an authorized insider may not trigger. DC-GUARDIAN presents such links only as context, never as evidence of compromise.
