---
name: init-instance
description: Create a new strategy workspace instance for a company or business unit, or upgrade the engine-owned files of an existing one. Use when the user wants to start a strategy workspace, set one up for another company, or refresh CLAUDE.md, rules and scripts after a plugin update.
---

# init-instance

An instance is one company's strategy: a repository with `strategy.config.yaml` and content.
Everything company-specific goes into the instance. Never write company facts into this plugin.

## Create

1. Ask for the target directory, company, business unit (optional) and content language.
2. Run `python3 <this skill dir>/scaffold.py <target> --company "<name>" --unit "<unit>" --language <code>`.
3. Fill `strategy.config.yaml` with the user: description and users. Leave `frameworks_active` empty.
   Segments are not configuration: they are entities in `diagnosis/market/`.
4. Write the purpose in `framing.md` with the user: why the company exists (`^why`), how it means to
   win (`^how`) and what it offers (`^what`), one block each. It is a stated intention and needs no claims.
   Then ask whether the user already has the strategic questions:
   - Yes: write at most five in `framing.md`, one line each: `- Question? (status:: open) ^q01`. A question is
     strategic if its answer would change where the company plays or how it wins. Reject questions that are
     tasks. The diagnosis areas stay pending; when a framework first needs a segment, create it with an area
     update of `diagnose` on `market`.
   - No: run the full pass of `diagnose`, which ends with the questions in `framing.md`, then come back here.
5. Draft `strategy/direction.md` as a first guess, with every guess written as an explicit hypothesis
   to test. This comes before any source capture: it tells you which evidence is worth collecting.
6. For each open question, list the evidence that is missing and the framework that would answer it.
   Add those frameworks to `frameworks_active`. Missing evidence that would change a decision is a gap (rule 3).
7. Create the venv: `python3 -m venv <target>/.venv && <target>/.venv/bin/pip install -r <target>/requirements.txt`.
   Tell the user to activate it (`source .venv/bin/activate`) before starting Claude Code in the instance.
8. Run `<target>/.venv/bin/python <target>/scripts/check.py <target>` and fix anything it reports.
9. Suggest `git init` and a first commit.

Then hand over to `ingest-source`, `apply-framework` and `record-decision`, in that order, one question at a time.

## Upgrade

`python3 <this skill dir>/scaffold.py <target> --upgrade` overwrites `CLAUDE.md`, `_dashboard.md`,
`.claude/rules/` and `scripts/`, adds template files the instance lacks (such as `requirements.txt`)
without overwriting any, and deletes engine files an earlier version shipped (`scripts/trace.py`, now
`scripts/check.py`). Queries of the user's own belong in another note: the dashboard is replaced on
every upgrade. It never touches configuration or content, and never creates `diagnosis/`: an existing
instance gets it by running `diagnose`, which creates the area files from the templates. If the
configuration still has `segments`, `scripts/check.py` warns: move them to entities in
`diagnosis/market/` and delete the key. Lines added to the template `.gitignore` do not reach an
existing instance: show the user the difference. Run `scripts/check.py` afterwards.
