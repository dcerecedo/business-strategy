---
name: record-decision
description: Record or review a strategic decision in a strategy workspace instance, with its supporting conclusions, falsifiable hypotheses, pre-mortem and review signals, and update direction and OKRs. Use when the user makes, changes or revisits a strategic choice, or when a hypothesis is refuted or overdue.
---

# record-decision

Read `strategy.config.yaml`, `framing.md` and `.claude/rules/decisions.md` first. Pull from git before
taking a new number.

## Record

1. State the decision in one sentence and the question it answers.
2. Link the conclusions it rests on. If there are none, it is not ready: go to `apply-framework`.
3. List the alternatives discarded and why. Options the analysis raised belong here.
4. Pre-mortem: "It is two years from now and this decision failed. Why?" Turn each credible cause into
   either a hypothesis (metric, threshold, deadline, metric source, owner) or a review signal.
5. Check budgets: live decisions and hypotheses per decision. Over the soft limit, close or merge first.
6. Write `decisions/D-NNN-<slug>.md` with status proposed, and each `hypotheses/H-NNN-<slug>.md`.
7. When the user confirms it, set status active. If it answers a question, mark that question
   `(status:: answered) (answered_by:: [[D-NNN-<slug>]])` in `framing.md`.
8. Update `strategy/direction.md` and the current `strategy/OKR-YYYY.md` so they link the decision.
   Direction must still read in one page. If the decision changes why, how or what in the purpose of
   `framing.md`, rewrite that block and add `(changed_by:: [[D-NNN-<slug>]])`.
9. Run `python3 scripts/check.py .`.

## Review

Triggered by the Affected section of a report, a refuted or overdue hypothesis, or a review date.

1. Read the chain behind the decision down to the claims.
2. With the user, choose: keep (update `review`), revise (new decision that `supersedes` this one), or
   withdraw (status superseded, with the reason in the body).
3. Update hypothesis statuses only with data from their `metric_source`.
4. Run `python3 scripts/check.py .`.
