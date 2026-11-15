---
name: ingest-source
description: Turn a document, URL, interview note or dataset into a source file with cited claims in a strategy workspace instance. Use when the user provides new evidence, a triaged signal, or asks to capture or refresh a source.
---

# ingest-source

Work inside an instance (a directory with `strategy.config.yaml`). Read the configuration and
`framing.md` first, and the format in `.claude/rules/sources.md`.

1. Name the open question or live decision this source bears on. If there is none, stop and say so:
   the source is not kept (rule 1).
2. Save a copy of the original in `originals/` with the same stem as the source file.
3. Create `sources/S-<capture date>-<slug>.md`. Extract only claims that bear on step 1: literal
   quotes, or `DATA:` lines for tables, computed figures and interview notes.
4. Check each quote against the original, word for word. Drop any you cannot find.
5. Compare each claim with existing claims on the same question. Mark `(confirms:: ...)` or
   `(contradicts:: ...)` where it applies. Do not edit the older claim.
6. Set `review` from `review_months` in the configuration.
7. Run `python3 scripts/trace.py .` and show the user the Affected section. Do not change any
   status: the user decides what a contradiction means.
