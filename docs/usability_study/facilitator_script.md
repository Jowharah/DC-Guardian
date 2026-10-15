# Facilitator script

Read the parts in *italics* aloud. Do not explain the interface, do not say whether an answer is right, and help only when the participant asks or has been stuck for 3 minutes; record any help on the observation sheet.

## Before the first session (once)

1. **Back up the data:** `python -m presentation.backend.app.backup create` (options in `docs/VALIDATION_AND_OPERATIONS.md`, Operations routine).
2. **Start the system:** backend and frontend (see `CLAUDE.md`), with `DCG_INVESTIGATOR_ENABLED=0` unless task T8 is planned.
3. **Prepare the data:** in **Scenario Lab**, run the synthetic scenarios the tasks need, so that the Monitoring Center shows:
   - at least one correlated group at HIGH severity;
   - one PPE observation without a human verdict;
   - one investigation in state OPEN.
4. **Pilot run:** do the tasks yourself once and fill in `answer_key.md` with the correct answers for this exact data.
5. **Equipment:** prepare the PPE test image for optional T9, a timer and printed sheets.

## Before each session

- Restore the same starting state: no verdict on the T4 observation, the T5 investigation back to OPEN. Either undo through the interface, or restore the backup and re-run the same scenarios.
- Open the dashboard on the **Monitoring Center**, logged in, at normal zoom.

## Welcome and consent (read)

*Thank you for helping. We are testing a prototype monitoring dashboard for a data centre. It combines alerts about cyber attacks, safety equipment, people at doors, equipment health and room conditions. We are testing the software, not you: if something is hard, that is useful for us to know.*

*Please think aloud: say what you are looking for, what you expect and what surprises you. I will give you tasks one at a time. I cannot help much during a task, because we want to see how the dashboard works on its own, but you can give up on any task at any time.*

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
