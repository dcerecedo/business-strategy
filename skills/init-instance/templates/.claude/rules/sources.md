---
paths:
  - "sources/**"
---
# Source format

```markdown
---
type: source
origin: Publisher, title
url: https://...
published: 2026-10-24
captured: 2026-11-15
review: 2027-05-15
original: originals/S-20261115-short-slug.pdf
---
- "Literal quote." (confidence:: high) (locator:: p. 4, section 2) ^c01
- DATA: 1,240 units in 2025, summed from table 3. (confidence:: medium) ^c02
```

- A quote is always literal and continuous, with no ellipses. What has no sentence to quote (a table,
  a computed figure, an interview note) is a `DATA:` line stating the value, how it was obtained and
  from where.
- Where the quote is in the original goes in `(locator:: ...)`, never as text after the quote.
- A quote that is not in the text layer and was checked on a page image adds `(verified:: manual)`.
- Extract only claims that bear on a decision or an open question (rule 1).
- Confidence is high, medium or low by source and method, never by convenience.
- An internal opinion is a source with `origin: internal, <person>`; low confidence unless it brings data.
- Keep a copy of the original in `originals/` so quotes can be verified if the URL changes: the file
  as served (PDF, HTML), not an extract. `scripts/check.py` rejects any other original for a source
  with a `url`; a source without one (interview, internal note) may keep a `.md` or `.txt`.
  It checks every quote, and every quoted fragment of three words or more in a `DATA:` line, against it.
  The original has the same name as the source file; a `.txt` extract may sit next to it.
- Every value in a `DATA:` line is readable in the original of the same source. `scripts/check.py`
  lists the numbers it does not find there, so a person reviews computed values.
- A price states currency, tax (included, excluded or not stated), date and scope (material or installed).
- A comparison between two sources quotes the fragments it compares.
- A new claim that clashes with or backs an existing one adds
  `(contradicts:: [[S-...#^c01]])` or `(confirms:: [[S-...#^c01]])`. `scripts/check.py` checks that
  the claim it points to exists.
- `review` defaults from `review_months` in the configuration.
