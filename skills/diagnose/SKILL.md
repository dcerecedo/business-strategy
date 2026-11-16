---
name: diagnose
description: Study a company and its context area by area in a strategy workspace instance (macro, market, ecosystem, competition, segments, offering, go to market, business model, capabilities, results), record cited baselines, entities (segments, competitors) and findings, and raise strategic questions of kind game, risk or opportunity. Use when the strategic questions are not known yet, when game.md is due for review, or when something changes in one area (a new competitor, a lost segment, a new rule).
---

# diagnose

The diagnosis describes and flags. It applies no framework: depth comes later with `apply-framework`.
Its output is questions in `framing.md`. "How do we get there" is not a diagnosis output: it is an
ordinary question, answered by `apply-framework` and then `record-decision`.

Read `strategy.config.yaml`, `framing.md` (the purpose first) and `.claude/rules/diagnosis.md` first.
Load `ingest-source` before capturing any evidence, also when a subagent does the capture.
If the instance has no `diagnosis/`, copy `templates/diagnosis/` from the `init-instance` skill of this
plugin into it: every area starts pending. Then move any `segments` left in the configuration to segment
entities and delete the key.

## Full pass

At instance creation when the user has no questions yet, and when `game.md` is due for review.

1. Walk the areas in the order of the rules file, context first. For each one:
   1. Ask the user what they know, then capture evidence with `ingest-source`, giving the area as the
      reason to keep the source. What the user knows without a document is an internal source.
   2. Admit only facts that change the baseline, a finding or an entity attribute.
   3. Write the baseline: at most five lines, each citing claims.
   4. Create the entities the area takes, applying its membership test before each one. Segments may
      start as working definitions resting on an internal source.
   5. Write findings with status `new`: interpretations that could raise a question, each citing claims.
   6. Set `status`, `updated` and `review`. An area with nothing material is `not_material` with the
      reason; one whose evidence cannot be had yet is `gap`, naming what is missing. Never skip an area.
2. Write `game.md`: one paragraph on where the company plays and how it wins today, from the areas,
   set against why, how and what. A difference between the two is a `game` finding in the area it shows.
3. Propose candidate questions grouped by kind (game, risk, opportunity), each with the findings behind
   it. A question is strategic if its answer would change where the company plays or how it wins.
4. The user picks at most five. Write each as `- Question? (status:: open) (kind:: risk) (raised_by:: [[competition#^f01]]) ^qNN`.
   Check the `open_questions` budget first.
5. Classify every finding with the user: `raised` if a question cites it, `parked` otherwise.
6. Run `python3 scripts/check.py . --focus diagnosis` and fix validation errors.

## Area update

When the user names one area and what changed. Never rerun the whole pass for this.

1. Capture the evidence with `ingest-source`.
2. Create or update the entity, or archive it if its subject stopped mattering.
3. Rewrite the baseline only if the current state changed.
4. Add findings as `new`. A finding that stopped being true becomes `retired`; one whose meaning changed
   is retired and replaced by a new one. Never renumber or delete a finding a question cites.
5. Classify each new finding with the user: it raises a new question (status `raised`; check the
   `open_questions` budget), it is added to the `raised_by` of an open question (status `raised`), or it is
   `parked`.
6. Set `updated` on the area.
7. Run `python3 scripts/check.py . --focus diagnosis` and show the user the questions to revisit, the
   Affected rows for findings and questions, and whether `game.md` needs rewriting. Change no status
   the user has not decided.
