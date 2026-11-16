# IDs and links

| Piece | Unit | Folder | ID example |
| --- | --- | --- | --- |
| Purpose | Block in `framing.md` | root | `framing#^why`, `framing#^how`, `framing#^what` |
| Strategic question | Block in `framing.md` | root | `framing#^q02` |
| Source | File | `sources/` | `S-20261115-short-slug` |
| Claim | Block in its source | `sources/` | `S-20261115-short-slug#^c01` |
| Gap | Block in `framing.md` | root | `framing#^g01` |
| Diagnosis area | File | `diagnosis/` | `competition` |
| Finding | Block in its area | `diagnosis/` | `competition#^f03` |
| Entity | File | `diagnosis/<area>/` | `planify`, `independents` |
| Game | File | `diagnosis/` | `game` |
| Conclusion | File | `conclusions/` | `C-porter-03` |
| Decision | File | `decisions/` | `D-007-short-slug` |
| Hypothesis | File | `hypotheses/` | `H-012-short-slug` |
| OKR | File per year | `strategy/` | `OKR-2027` |

- Numbers are sequential and never reused. The slug is only for reading.
- Sources use the capture date instead of a number. Areas use their fixed name; entities a short slug
  of their subject.
- The ID is the wikilink target: `[[S-20261115-short-slug#^c01]]`. There is no second identifier.
- All links point backwards: OKR and direction to decisions, decisions to conclusions and hypotheses,
  conclusions to claims, questions to the findings that raised them (`raised_by`), findings to claims,
  purpose blocks to the decision that changed them (`changed_by`). Never add a field that points forwards.
- File names are unique across the whole instance, so views are `<area>-view.md`.
