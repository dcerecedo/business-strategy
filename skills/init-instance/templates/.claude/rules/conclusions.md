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
---
# The conclusion as one sentence

## Fact
## Interpretation
## Implication
```

- `supports` cannot be empty (rule 5). `question` is mandatory (rule 9).
- `against` is mandatory even when empty: look for contrary evidence before leaving it empty.
  It holds claims that cut against the title, not the company's own marketing or unchecked items.
- Framework fields (`power`, `force`...) are listed in the framework catalog and are mandatory.
- Status is current or archived.
- One conclusion per file, numbered per framework: `C-<framework>-NN`.
- Headings are written in the configured language; keep the three-part structure (rule 6).
