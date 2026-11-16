---
name: ingest-source
description: Turn a document, URL, interview note or dataset into a source file with cited claims in a strategy workspace instance. Use when the user provides new evidence, a triaged signal, or asks to capture or refresh a source.
---

# ingest-source

Work inside an instance (a directory with `strategy.config.yaml`). Read the configuration and
`framing.md` first, and the format in `.claude/rules/sources.md`.

Capture: when a page rejects plain requests or needs JavaScript, open it with Claude in Chrome
(`mcp__claude-in-chrome__*` tools) if the session has them. A paid document is a gap with origin
`purchase`. If you delegate capture to a subagent, copy this paragraph and steps 2 to 4 into its prompt.

1. Name the open question or live decision this source bears on. If there is none, stop and say so:
   the source is not kept (rule 1).
2. Save the original in `originals/` with the same stem as the source file, as served: the PDF as
   downloaded, or the page's HTML (from Chrome: `document.documentElement.outerHTML`). A text
   extract may sit next to it (`.txt`), never instead of it.
   Every value in a `DATA:` line must be readable in this original. A fact seen on another site
   (a registry status on an aggregator, a search result count) is a separate source with its own
   original, or a gap.
3. Create `sources/S-<capture date>-<slug>.md`. Extract only claims that bear on step 1: literal
   quotes, or `DATA:` lines for tables, computed figures and interview notes. Before quoting a legal
   or technical provision, read the whole article or section and state in the locator who or what
   it applies to.
4. Check each quote against the original, word for word. Drop any you cannot find. If the text layer
   is unusable and you checked a page image, add `(verified:: manual)`.
5. Compare each claim with existing claims on the same question. Mark `(confirms:: ...)` or
   `(contradicts:: ...)` where it applies. Do not edit the older claim. Report how many you marked;
   zero across several sources on one question needs a reason.
6. Set `review` from `review_months` in the configuration.
7. Run `python3 scripts/trace.py .` and show the user the Affected section, any quote or quoted
   fragment that failed, the quotes cut before a condition and the `DATA:` values not found.
   Do not change any status: the user decides what a contradiction means.
