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
3. Explore with the user, following the framework's own rule in `frameworks.md`.
4. Filter. A finding becomes a conclusion only if it supports or challenges a decision, proposed or
   live. Check the `conclusions_per_framework` budget before writing; over the soft limit, merge or
   archive first.
5. Write each conclusion as `conclusions/C-<framework>-NN.md`: fact, interpretation, implication,
   each fact tied to a claim in `supports`.
6. Argue the other side. For each conclusion, search the sources for contrary evidence and put it in
   `against`. If you find none, say what would count as contrary evidence.
7. Run `python3 scripts/trace.py .` and fix validation errors.
