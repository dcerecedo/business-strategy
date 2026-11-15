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
3. Fill `strategy.config.yaml` with the user: description, users, segments. Leave `frameworks_active` empty.
4. Fill `framing.md` with the user: company, segments, and at most five strategic questions.
   Each question is one line: `- Question? (status:: open) ^q01`. A question is strategic if its
   answer would change where the company plays or how it wins. Reject questions that are tasks.
5. Draft `strategy/direction.md` as a first guess, with every guess written as an explicit hypothesis
   to test. This comes before any source capture: it tells you which evidence is worth collecting.
6. For each open question, list the evidence that is missing and the framework that would answer it.
   Add those frameworks to `frameworks_active`. Missing evidence that would change a decision is a gap (rule 3).
7. Run `python3 scripts/trace.py <target>` and fix anything it reports.
8. Suggest `git init` and a first commit.

Then hand over to `ingest-source`, `apply-framework` and `record-decision`, in that order, one question at a time.

## Upgrade

`python3 <this skill dir>/scaffold.py <target> --upgrade` overwrites `CLAUDE.md`, `.claude/rules/` and
`scripts/`. It never touches configuration or content. Run `scripts/trace.py` afterwards.
