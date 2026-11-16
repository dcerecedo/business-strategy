---
paths:
  - "diagnosis/**"
---
# Diagnosis format

The diagnosis is the instance's knowledge of the company and the landscape it plays in. It describes
and flags; it applies no framework. Its purpose is to raise questions (rule 9): is this the game we
want to play (`game`), which risk to mitigate (`risk`), which opportunity to take (`opportunity`).

Four kinds of item, with different rules:

| Kind | Items | Changes | Kept because |
| --- | --- | --- | --- |
| Evidence | claims in `sources/` | never | something cites it |
| Knowledge | area baselines, entities, `game.md` | rewritten to the current state | it describes the landscape |
| Interpretation | findings | never; retire and add a new one | it raises or could raise a question |
| Commitment | decisions, hypotheses, direction | see decisions rules | as there |

Admit a fact only if it changes a baseline, a finding or an entity attribute. The rest stays in its source.

## Areas

One file per area, always present, walked in this order:

| Area | Block | Covered when it answers |
| --- | --- | --- |
| `macro` | context | Which economic, social or technology change reaches our segments within the planning horizon? |
| `market` | context | Which segments exist, how big, growing or shrinking? (segment entities live here) |
| `ecosystem` | context | Which suppliers, partners and rules could stop or change delivery? |
| `competition` | context | Who each segment would hire instead of us, how they position and price, what they did lately; substitutes and doing nothing included |
| `segments` | company | Which segments we serve and which not, and why |
| `offering` | company | What we sell, to whom, at what price, at what stage |
| `go_to_market` | company | How each served segment finds, buys and is onboarded |
| `business_model` | company | How we make money and what it costs: margins, unit economics as they are, without the framework |
| `capabilities` | company | What people, technology, operations and assets we rely on, and what we lack |
| `results` | company | What the numbers say and which way they trend |

```markdown
---
type: area
area: competition
block: context
status: covered
updated: 2026-11-15
review: 2027-05-15
---
# Competitors and substitutes

## Baseline
Three rivals sell to independents; one bundles planning in its ERP. [[S-20261102-planify-pricing#^c01]]

## Findings
- A bundled ERP prices shift planning at zero for its users. (kind:: risk) (status:: raised) (supports:: [[S-20261102-planify-pricing#^c01]]) (about:: [[planify]]) ^f01
```

- `status` is pending, covered, not_material or gap. `not_material` says why in the body; `gap` names
  the missing evidence. Every area is visited: none is skipped silently.
- `## Baseline` and `## Findings` are fixed headings, like `## Gaps` in `framing.md`; the title and prose use
  the configured language.
- Baseline: what is true now, at most five lines, each citing at least one claim.
- A finding is an interpretation of the baseline that could raise a question. If no question could follow
  from it, it belongs in the baseline.
- Finding fields: `kind` (game, risk, opportunity), `status`, `supports` (claims, never empty), optional
  `about` (entities it interprets). IDs `^fNN` are never renumbered.
- Finding status: `new` until the user classifies it; then `raised` (a question cites it in `raised_by`),
  `parked`, or `retired` when it stops being true. Do not edit a finding's meaning: retire it and add a
  new one. Do not delete a finding a question cites.
- `updated` is the date the baseline or findings last changed. `review` defaults from `review_months`
  (`area_context` or `area_company`).
- Findings live only in area files; `findings_per_area` counts those not retired.

## Entities

`diagnosis/<area>/<entity>.md`: a subject the claims are about. The entity describes; the area interprets.

| Area | Entity | It counts when | Not one when |
| --- | --- | --- | --- |
| `market` | segment | its buyers respond the same way to an offer and differently from the nearest segment, and the difference changes what they pick or pay | it cannot be identified or reached, or the difference changes neither choice nor price |
| `competition` | competitor | at least one segment would hire it instead of us; substitutes and doing nothing count | it is in our industry but no segment weighs us against it |
| `offering` | line (only with more than one) | it differs from the other lines in buyer, price or go-to-market | an add-on or tier sold the same way to the same buyer |
| `ecosystem` | dependency (only critical ones) | losing it would stop or materially change delivery within the planning horizon, including rules that apply | a supplier we could replace without changing how we deliver |

Other areas have no entities.

```markdown
---
type: entity
area: competition
relevance: high
status: active
review: 2027-05-15
segments: ["[[restaurant-groups]]"]
proposition: shift planning bundled in an ERP
pricing: 39 EUR per site per month
size: unknown
recent_move: ERP plan launched 2026-11
---
- Bundles planning in the ERP plan. [[S-20261102-planify-pricing#^c01]]
```

- Common fields: `area` (the folder), `relevance` (high, medium, low), `status` (active, watch, archived), `review`.
- Fixed attributes per area; every key is present, empty if unknown:
  - segment: `profile` (the proxy used to find and reach it, not the segment), `criteria` (what they value),
    `willingness_to_pay`, `buying_process`, `channels`, `alternatives` (links to competitors), `size`,
    `served` (served, not_served), `basis` (working, evidenced). The body has a `Distinct from` line naming
    the nearest segment and the axis that separates them, and one line each for identifiable, reachable,
    worth a tailored approach and stable. A working segment rests on an internal source; an evidenced one
    fills `criteria`, `alternatives` and `size`.
  - competitor: `segments` (links to segments), `proposition`, `pricing`, `size`, `recent_move`.
  - line: `segments` (links to segments), `proposition`, `pricing`, `stage`.
  - dependency: `role` (supplier, partner, regulator), `dependency`, `alternatives`.
- Frontmatter holds short labels for the views. Every fact, number included, is a body line citing a claim.
  An entity that is not archived cites at least one.
- No findings in entity files. Conclusions cite claims, never entities; a conclusion's `segment` links a segment.
- Jobs to be done are `jtbd` conclusions linked to a segment, not entities or attributes: the diagnosis
  applies no framework.
- Archive an entity (status archived) when its subject stops mattering, not because nothing links it.
- `entities_per_area` applies to offering and ecosystem only.

## Views and game

- `diagnosis/<area>-view.md` holds only Dataview queries over the entities of an area (the suffix keeps file
  names unique). `segments-view.md` shows the segments served and not served, with their jtbd conclusions.
- `diagnosis/game.md`: `type: game`, `updated`, `review`. One paragraph: where the company plays and how it
  wins today, derived from the areas, set against `[[framing#^why]]`, `[[framing#^how]]` and `[[framing#^what]]`.
  A gap between the two is a `game` finding. Rewrite it when an area changes after it.

## Checks

`scripts/check.py` checks all of this only when `diagnosis/` exists. It fails on a missing area or one
without a valid status, a baseline line without a claim, a finding without `supports`, invalid values, an
entity missing a field or citing no claim, and broken or plain-text links in `raised_by`, `about`,
`segment` and entity attributes. It lists pending areas, findings still `new`, questions whose finding
is retired or reached by an alert, `game.md` older than an area, stale knowledge and budgets. It cannot
see that a finding's text was edited: that is why findings are retired, not rewritten.
