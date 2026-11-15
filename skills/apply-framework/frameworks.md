# Framework catalog

Candidates, not a route. An instance activates only what its open questions need.

| Framework | Answers | Extra frontmatter | Own rule |
| --- | --- | --- | --- |
| `porter` | How attractive is this segment, and who holds the power? | `force`, `intensity` (high, medium, low), `segment` | One conclusion per force and segment, never the industry in the abstract. |
| `jtbd` | What is the customer trying to get done, and what do they use today? | `segment`, `job` (when..., I want..., so that...), `current_alternative` | At least one claim from a customer; internal opinion is not enough. |
| `sizing` | How big is the reachable market? | `method` (bottom_up), `tam`, `sam`, `som` (currency per year) | Bottom-up only. Every input figure cited, the arithmetic in the body. |
| `value_chain` | Where do we create cost or differentiation in operations? | `activity`, `effect` (cost, differentiation), `compared_with` | Always against a named competitor. |
| `unit_economics` | Does the model pay for itself? | `segment`, `cac`, `ltv`, `gross_margin`, `payback_months` | Figures from internal data sources, each one a `DATA:` claim. |
| `seven_powers` | What makes the advantage last? | `power`, `benefit`, `barrier` (both lists of claim links) | Check all seven powers in the session; write a conclusion only for those with a cited benefit. A power is shown only with a cited barrier; with `barrier: []` the title says it is not shown. Counter-positioning is about a business model the incumbent cannot copy without harming itself, not a technology. |
| `pestel` | Which outside change affects a segment? On demand only. | `factor`, `horizon_years` | Only factors with an effect on a named segment. |
| `positioning` | How do customers tell alternatives apart? On demand only. | `axis_x`, `axis_y` | Axes are the criteria customers use to choose, with a claim for each. |
| `wardley` | What should we build, buy or wait for? On demand only. | `component`, `stage`, `movement` | The stage carries a claim; the movement is the conclusion. |

Not in the catalog on purpose:

- SWOT and TOWS reclassify conclusions that already exist. Use a `sign` field if a view is wanted.
- VRIO overlaps with 7 Powers, which is stricter.
- Playing to Win overlaps with the direction structure (diagnosis, guiding policy, coherent actions).
  Its best part, "what would have to be true", is the hypotheses of each decision.

Add a framework when a real question needs one: a row here with what it answers and its own rule.
