---
name: apply-framework
description: Answer a strategic question of a strategy workspace instance with a framework (Porter, JTBD, market sizing, value chain, unit economics, 7 Powers and others) and record only the conclusions that matter. Use when the user wants to analyse market, competition, customers or internal capabilities for an open question.
---

# apply-framework

A framework is a way to question the evidence, not a form to fill. The exploration stays in this
session. Only conclusions are written (rule 9).

Read `strategy.config.yaml`, `framing.md` and `.claude/rules/conclusions.md` first.

1. Pick the open question. Pick the framework that answers it from `frameworks.md` in this skill's
   directory. If it is not in `frameworks_active`, propose adding it and say why this question needs it.
2. List the evidence the framework needs. Read the claims that exist. What is missing and would change
   a decision is a gap: name it and stop to capture it with `ingest-source` if the user agrees.
   Load `ingest-source` before capturing, also when a subagent does the capture.
3. Explore with the user, following the framework's own rule in `frameworks.md`. Show the findings
   as candidate conclusions, one line each with the claims behind it, and wait before writing files.
4. Filter. A finding becomes a conclusion only if it supports or challenges a decision, proposed or
   live. Check the `conclusions_per_framework` budget before writing; over the soft limit, merge or
   archive first.
5. Write each conclusion as `conclusions/C-<framework>-NN.md`: fact, interpretation, implication.
   Every sentence of the fact section rests on a claim in `supports`. A statement about what buyers,
   installers or inspectors do needs a claim; without one it is a gap, not an interpretation.
   Compare prices only on the same basis (tax, year, material or installed); otherwise say the
   basis differs and do not compute a ratio.
6. Argue the other side. For each conclusion, search the sources for contrary evidence and put it in
   `against`: claims that cut against the title sentence. The company's own marketing and lines that
   only say something was not checked do not count. If you find none, leave `against: []` and say
   what would count as contrary evidence.
7. Run `python3 scripts/trace.py .` and fix validation errors.
8. Close with the answer the conclusions give to the question in one paragraph, naming the
   conclusions it rests on, and the gaps in `framing.md` in the format of `.claude/rules/gaps.md`.
