---
paths:
  - "decisions/**"
  - "hypotheses/**"
  - "strategy/**"
---
# Decision, hypothesis and strategy formats

## Decision

```markdown
---
type: decision
status: proposed
conclusions: ["[[C-porter-03]]"]
hypotheses: ["[[H-012-short-slug]]"]
supersedes:
review: 2027-05-15
---
# D-007 The decision as one sentence

## Context
## Decision
## Alternatives discarded
## Review signals
```

- Status is proposed, active, under_review or superseded.
- A superseded decision is never deleted: the new one links it in `supersedes`.
- Review signals are observable events that would force a review. They drive what is monitored.

## Hypothesis

```markdown
---
type: hypothesis
metric: trial-to-paid conversion
threshold: ">= 8 %"
deadline: 2027-03-31
metric_source: billing export
owner: name
status: open
---
The falsifiable statement in one sentence.
```

- Status is open, confirmed or refuted. No metric and threshold means it is an assumption, not a hypothesis.
- A hypothesis does not link its decision: the decision links the hypothesis.

## Strategy

- `strategy/direction.md`: `type: direction`, `decisions: [...]`, sections diagnosis, guiding policy, coherent actions.
- `strategy/OKR-YYYY.md`: `type: okr`, `decisions: [...]`, objectives with key results.
- Direction must read in one page for someone who does not use the workspace.
