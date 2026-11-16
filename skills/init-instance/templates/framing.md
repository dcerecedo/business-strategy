---
type: framing
review:
---
# Framing

## Purpose

Three blocks written with the user: `- Why ... ^why`, `- How ... ^how`, `- What ... ^what`.
Only a decision changes them; the block then adds `(changed_by:: [[D-NNN-slug]])`.

## Company

## Segments

Defined only as entities in `diagnosis/market/`: [[segments-view]].

## Strategic questions

One per line, at most five open: `- Question? (status:: open) ^q01`
Status is open, answered or retired. An answered question adds `(answered_by:: [[D-NNN-slug]])`.
A question may add `(kind:: game|risk|opportunity)` and, if diagnosis findings raised it,
`(raised_by:: [[competition#^f01]], [[market#^f02]])`.
