# DC-GUARDIAN usability study: protocol

**Prepared:** 2026-10-15. This closes the gap in the proposal's evaluation plan: usability was promised and not yet measured.

| File | Who uses it | Purpose |
|---|---|---|
| `README.md` (this file) | Team | Aims, design, measures, ethics, analysis |
| `facilitator_script.md` | Facilitator | Checklist, consent, what to say, debrief |
| `answer_key.md` | Facilitator only | Correct answers for this session's data (fill in during the pilot) |
| `participant_tasks.md` | Participant | One card per task (print, or show one at a time) |
| `observation_sheet.md` | Note-taker | Success, time, errors and help per task |
| `questionnaire.md` | Participant | Background, per-task ease, SUS, concept check, trust |
| `results_template.csv` | Note-taker | One row per participant: enter the paper sheets here |

Score with `python presentation/backend/validation/usability_score.py docs/usability_study/results.csv`. It writes `docs/usability_study/results_summary.md`.

## 1. Aims

Can a person who did not build DC-GUARDIAN:
1. find what needs attention and how severe it is (Monitoring Center);
2. understand **why** events were grouped, and what the system does *not* claim (correlation is contextual, not causal);
3. record a human verdict and move an investigation through its states correctly;
4. find work waiting for review, and summary figures;
5. come away with a correct, calibrated understanding of the system's limits: rules set severity, detectors can be wrong, there is no autonomous action.

## 2. Design

- **Participants:** 3–5 people outside the project team, for example classmates, ideally one with IT operations or security experience. Five participants find most major usability problems (Nielsen & Landauer, 1993); results are formative, not statistically representative.
- **Session:** one participant at a time, about 35–40 minutes, on the operator PC.
  - Roles: a facilitator (reads the script, does not help unless asked) and, if possible, a separate note-taker.
- **Method:** think-aloud while doing 7 core tasks (plus 2 optional ones), then the questionnaire and a short debrief.
- **Data:** synthetic scenarios and controlled test images only; no real personal data.
- **Account:** the local administrator account, because correlated groups and verdicts are administrator features.
- **AI Investigator:** off by default (`DCG_INVESTIGATOR_ENABLED=0`). Optional task T8 uses it only if the team agrees beforehand; it sends synthetic Evidence to OpenAI.

## 3. Measures

| Measure | How | Interpretation |
|---|---|---|
| Task success | Per task: 1 = success, 0.5 = success with help or a wrong detail, 0 = failure or gave up | Success rate per task |
| Time on task | Seconds from reading the card to the answer | Median per task |
| Errors | Wrong clicks or paths that needed backtracking | Count per task |
| Single Ease Question (SEQ) | After each task, 1 (very difficult) to 7 (very easy) | Mean per task; below about 5 flags a hard task |
| System Usability Scale (SUS) | 10 standard items after all tasks (Brooke, 1996) | 0–100. About 68 is the cross-study average; above 80 is good |
| Concept check | 6 true/false statements about what the system claims | Share correct; shows whether the safeguards are understood |
| Trust and clarity | 5 statements, 1–5 agreement | Calibrated trust, not maximum trust, is the goal |
| Problems | Observed issues, rated 0–4 for severity (Nielsen) | Prioritised fix list |

## 4. Procedure (per participant)

1. Welcome, consent and background questions (5 min).
2. A 2-minute neutral overview (script). The participant explores freely for 2 minutes.
3. Tasks T1–T7 (optional T8–T9), one card at a time, with the SEQ after each (20–25 min).
4. SUS, concept check, trust items (5 min).
5. Debrief questions (5 min).

Between participants, run the reset steps in the facilitator script so everyone sees the same state.

## 5. Ethics and data handling

- Participants are adults who volunteer and may stop at any time. The study tests the software, not the person.
- **Identifiers:** none recorded. Use codes P01–P05; no names, emails or recordings unless the participant agrees.
- **Storage:** notes and sheets stay with the team. `results.csv` holds only codes and scores and may be committed; paper sheets and any recordings must not be.
- **Approval:** check your module's guidance on whether a low-risk classroom usability study needs any approval or a signed consent form; the consent text in the facilitator script can be printed and signed.

## 6. Analysis and reporting

For each task the script reports:
- success rate, median time and mean SEQ;
- SUS mean and range, and the concept-check score;
- trust items.

Add the observed problems by severity with a proposed fix for each. In the report, state n, the participants' backgrounds and the formative nature of the result. Do not generalise to production users.

## References

- Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In *Usability Evaluation in Industry*, Taylor & Francis.
- Sauro, J., & Dumas, J. S. (2009). Comparison of three one-question, post-task usability questionnaires. *Proceedings of CHI 2009* (Single Ease Question).
- Bangor, A., Kortum, P., & Miller, J. (2009). Determining what individual SUS scores mean. *Journal of Usability Studies*, 4(3).
- Nielsen, J., & Landauer, T. K. (1993). A mathematical model of the finding of usability problems. *Proceedings of INTERCHI 1993*.
