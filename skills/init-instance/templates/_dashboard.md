# Dashboard

Lists only. Alerts, budgets and reviews are in the latest report from `scripts/trace.py`.

## Latest report

```dataview
LIST FROM "reports" SORT file.name DESC LIMIT 1
```

## Open questions

```dataview
TABLE WITHOUT ID item.text AS "Question"
FROM "framing"
FLATTEN file.lists AS item
WHERE item.status = "open"
```

## Decisions

```dataview
TABLE status, review FROM "decisions" SORT status
```

## Hypotheses

```dataview
TABLE status, deadline, metric, threshold FROM "hypotheses" SORT deadline
```
