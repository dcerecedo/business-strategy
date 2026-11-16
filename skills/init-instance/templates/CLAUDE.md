# Strategy workspace instance

Engine-owned file: refreshed by `init-instance --upgrade`. Do not put company facts here.
Company, language, budgets and active frameworks are in `strategy.config.yaml`. Read it first.

## Purpose

Build and keep current the strategy of the company in the configuration: direction, decisions,
hypotheses and OKRs, each traceable back to literal evidence.

## Layers

1. Sources (`sources/`): one file per source; claims are blocks with a literal quote or a datum.
2. Diagnosis (`diagnosis/`, optional): one file per area of the company and its context, with a cited
   baseline and findings that raise questions; entities (segments, competitors) it describes; `game.md`.
3. Conclusions (`conclusions/`): one file per conclusion; each cites the claims that support it.
4. Decisions (`decisions/`, `hypotheses/`): ADR-style records with falsifiable hypotheses.
5. Strategy (`strategy/`): direction and yearly OKRs, linked to decisions.

Strategic questions in `framing.md` are the root: every conclusion answers one. They come from the user
or from a diagnosis finding (`raised_by`). The purpose (`framing.md`, why, how, what) is the context both
start from; only a decision changes it.
The core (framing, strategy, decisions, hypotheses) stays small. Evidence is only read by following links.

## Rules

1. Everything exists for a decision. Keep only what supports or challenges a decision, an open question
   or the diagnosis baseline.
2. Trace backwards, do not catalogue. Link from the decision to its support; no back-reference fields.
3. Record a gap only if closing it would change a decision; name the decision and what would change.
4. Budgets are explicit and live in the configuration.
5. No conclusion without at least one cited claim. Internal opinions are recorded as sources.
6. Separate fact, interpretation and implication in every conclusion.
7. Everything has a review date. Review what a live decision relies on and the diagnosis; archive the rest.
8. Each iteration ends with a shorter core, not with more layers.
9. Each analysis answers a framing question, not a template. A diagnosis area is the exception: its
   purpose is to raise questions, and it applies no framework.

## Setup

`scripts/check.py` needs PyYAML, installed in a venv inside the instance (ignored by git):

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Activate the venv before starting Claude Code, so `python3` resolves to it.

## Working here

- Keys, paths, IDs and status values are in English. Headings and prose use the configured language.
- Formats are in `.claude/rules/`. Follow them exactly: `scripts/check.py` does not read the rules, but checks part of what they say.
- After any change to content, run `python3 scripts/check.py .` and report what it says.
  `--focus diagnosis|framework|decision` puts the sections of that work first; errors are always global.
- The script never changes a status, and neither do you without the user deciding.
- Pull before creating a decision or hypothesis, so numbers do not collide.
