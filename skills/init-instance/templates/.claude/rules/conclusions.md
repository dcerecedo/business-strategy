---
paths:
  - "conclusions/**"
---
# Conclusion format

```markdown
---
type: conclusion
framework: porter
question: "[[framing#^q02]]"
supports: ["[[S-20261115-short-slug#^c01]]"]
against: []
status: current
review: 2027-05-15
force: substitutes
intensity: high
segment: "[[restaurant-groups]]"
---
# The conclusion as one sentence

## Fact
## Interpretation
## Implication
```

- `supports` cannot be empty (rule 5). `question` is mandatory (rule 9).
- `against` is mandatory even when empty: look for contrary evidence before leaving it empty.
  It holds claims that cut against the title, not the company's own marketing or unchecked items.
- Framework fields (`power`, `force`...) are listed in the framework catalog; `scripts/check.py` requires them.
  For `seven_powers`, `benefit` and `barrier` are lists of claim links and `benefit` cannot be empty.
  `scripts/check.py` rejects a claim that is both in `benefit` and in `against`.
- `segment` links a segment entity in `diagnosis/market/`, the only place segments are defined. When
  `diagnosis/` exists, `scripts/check.py` rejects plain text there. If the segment has no entity yet,
  create it first with `diagnose` (area update on `market`).
- `supports` and `against` cite claims, never entities or findings: read them to find the claims.
- Status is current or archived.
- One conclusion per file, numbered per framework: `C-<framework>-NN`.
- Headings are written in the configured language; keep the three-part structure (rule 6).
