# strategy-workspace

A Claude Code plugin to build and maintain a company strategy as plain files, readable in Obsidian.
Every decision traces back to the literal evidence that supports it.

The plugin is the engine. It contains nothing about any company. Each company (or business unit)
is an instance: its own repository, with a `strategy.config.yaml` and its content.

## Install

In Claude Code:

```
/plugin marketplace add dcerecedo/business-strategy
/plugin install strategy-workspace@business-strategy
```

Then ask Claude to create a strategy workspace instance; the `init-instance` skill takes it from there.

## Skills

| Skill | Use |
| --- | --- |
| `init-instance` | Create an instance, or upgrade its engine-owned files |
| `ingest-source` | Turn a document or URL into a source file with cited claims |
| `apply-framework` | Answer a framing question with a framework and keep only the conclusions |
| `record-decision` | Record a decision with its hypotheses, pre-mortem and review signals |

## Instance layout

```
strategy.config.yaml   company, language, active frameworks, budgets, review periods
framing.md             company, segments and strategic questions (^q01 ...)
sources/               S-YYYYMMDD-slug.md, one per source, claims as blocks (^c01 ...)
originals/             copy of each original, outside the graph
conclusions/           C-<framework>-NN.md
hypotheses/            H-NNN-slug.md
decisions/             D-NNN-slug.md
strategy/              direction.md, OKR-YYYY.md
reports/               impact-YYYYMMDD.md, written by scripts/trace.py
scripts/trace.py       validation, quote checks, alert propagation, budgets, reviews
requirements.txt       PyYAML, installed in the instance .venv/
CLAUDE.md, .claude/rules/   engine-owned, refreshed by init-instance --upgrade
```

Paths, IDs, frontmatter keys and status values are in English. Headings and prose are written
in the language set in `strategy.config.yaml`.

## Check

Each instance has its own venv for PyYAML, ignored by git:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/trace.py .
```

Activate the venv before starting Claude Code in the instance, so the skills' `python3` is the venv's. Exit code 1 on validation errors or a hard budget exceeded.
`trace.py` checks every literal quote against its file in `originals/`. PDFs need `pdftotext`
(poppler-utils); without it those quotes are listed as not checked.
`examples/acme` is a fictional instance with seeded alerts to try it on.

## Obsidian

Open the instance as a vault and install the Dataview community plugin for `_dashboard.md`.
The dashboard only lists; alert logic lives in `scripts/trace.py` alone.

## Two people, one instance

Sync with git. One file per unit keeps conflicts rare. Pull before creating a decision or
hypothesis: `trace.py` reports duplicated numbers if two people create the same one.

## License

MIT
