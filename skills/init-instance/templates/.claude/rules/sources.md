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
- "Literal quote." (confidence:: high) ^c01
- DATA: 1,240 units in 2025, summed from table 3. (confidence:: medium) ^c02
```

- A quote is always literal. What has no sentence to quote (a table, a computed figure, an interview
  note) is a `DATA:` line stating the value, how it was obtained and from where.
- Extract only claims that bear on a decision or an open question (rule 1).
- Confidence is high, medium or low by source and method, never by convenience.
- An internal opinion is a source with `origin: internal, <person>`; low confidence unless it brings data.
- Keep a copy of the original in `originals/` so quotes can be verified if the URL changes: the file
  as served (PDF, HTML), not an extract. `scripts/trace.py` checks every quote against it.
- Every value in a `DATA:` line is readable in the original of the same source.
- A price states currency, tax (included, excluded or not stated), date and scope (material or installed).
- A comparison between two sources quotes the fragments it compares.
- A new claim that clashes with or backs an existing one adds
  `(contradicts:: [[S-...#^c01]])` or `(confirms:: [[S-...#^c01]])`.
- `review` defaults from `review_months` in the configuration.
