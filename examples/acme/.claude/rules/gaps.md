---
paths:
  - "framing.md"
---
# Gap format

Gaps live in a `## Gaps` section at the end of `framing.md`, one block per gap:

```markdown
- What is missing. Would change: what the answer would become. (question:: [[framing#^q02]]) (origin:: internal) (priority:: vital) ^g01
```

- A gap names the question or live decision whose answer it would change, and how (rule 3).
  Changing a conclusion is not enough: say what that does to the answer.
- `origin` is one of internal, customer, installer, purchase, manual. `manual` is public but needs a
  person (blocked site, office visit).
- `priority:: vital` only if closing the gap could flip the answer. Keep vital gaps to three per question.
- `scripts/trace.py` checks that each gap has a `^gNN` id, a `question` that exists and a valid `origin`, and
  counts vital gaps per question against the `vital_gaps_per_question` budget.
- Gaps are numbered like claims (`^g01`) and closed by deleting the line once a source answers them.
