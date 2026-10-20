# Facilitator script

Read the parts in *italics* aloud. Do not explain the interface, do not say whether an answer is right, and help only when the participant asks or has been stuck for 3 minutes; record any help on the observation sheet.

## Before the first session (once)

1. **Build the fixed study inputs** (private folder `Documents\dcg-private\study_inputs`, never committed):
   `python docs/usability_study/prepare_study_data.py build-inputs`
2. **Equipment:** a timer and printed sheets. The upload files for optional T9 and T10 are in `study_inputs\participant_uploads\`.
3. **Pilot run (dry run):** prepare the data as below, do every task yourself once, and check the answers in `answer_key.md`.

## Before each session (about 5 minutes)

Every participant must see exactly the same dashboard. Verdicts and investigation changes are permanent by design, so the data is rebuilt from the same fixed inputs each time:

1. Close the **backend** window (the frontend can stay open), and make sure Neo4j is running in Neo4j Desktop.
2. Run `python docs/usability_study/prepare_study_data.py prepare`. It takes about 2–3 minutes and:
   - backs up the data;
   - clears local test Evidence, verdicts, reviews and investigation progress;
   - re-ingests the study inputs, with no OpenAI calls;
   - prints **READY for the session**.
3. Start the backend with the AI Investigator **on** for T8 (operator decision 2026-10-20): `DCG_INVESTIGATOR_ENABLED=1` (in `.env`, or in the window before starting), then run the backend command from `CLAUDE.md`. To run without T8, use `0` and skip the card.
4. Open the dashboard on the **Monitoring Center**, logged in, at normal zoom, and refresh the page.

## Welcome and consent (read)

*Thank you for helping. We are testing a prototype monitoring dashboard for a data centre. It combines alerts about cyber attacks, safety equipment, people at doors, equipment health and room conditions. We are testing the software, not you: if something is hard, that is useful for us to know.*

*Please think aloud: say what you are looking for, what you expect and what surprises you. I will give you tasks one at a time. I cannot help much during a task, because we want to see how the dashboard works on its own, but you can give up on any task at any time.*

*One optional task uses an AI assistant provided by OpenAI. Your question and the invented data are sent to OpenAI to produce an answer, so please don't type anything personal.*

*All the data is invented. We will not record your name; you are participant P__. Notes are kept by the project team and used only for our university project report. You can stop at any time without giving a reason. Is that all right?* (Record consent: yes / no. If they agree to audio recording, note it.)

## Overview (read, then 2 minutes of free exploration)

*Imagine you are an operator starting a shift. The system receives results from automatic detectors, groups results that happen close together in time and place, and sets a priority. You review what it shows and record your judgement. The system never acts on its own. Please take two minutes to look around before the first task.*

## During tasks

- Hand over one card at a time and start the timer when they finish reading.
- Stop the timer when they state their answer or give up.
- After each task, ask for the Single Ease Question: *Overall, how easy or difficult was this task, from 1, very difficult, to 7, very easy?*
- **Neutral prompts only:**
  - *What are you looking for?*
  - *What do you expect to happen?*
  - *What would you do next?*
  - Never: *try the menu on the left*.

## After the tasks

Give the questionnaire (`questionnaire.md`): SUS, concept check, trust items.

## Debrief (read and note answers)

1. *What was the most useful thing on the dashboard?*
2. *What was the most confusing thing?*
3. *Was it clear why some alerts were grouped together? What do you think the grouping means?*
4. *Did you understand where the severity came from?*
5. *If you used this every day, what is the first thing you would change?*

*Thank you, that is everything.*
