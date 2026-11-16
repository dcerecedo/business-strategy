# Dashboard

Lists only. Alerts, budgets and reviews are in the latest report from `scripts/check.py`.

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

## Diagnosis areas

```dataview
TABLE block, status, updated, review FROM "diagnosis" WHERE type = "area" SORT block DESC, file.name
```

## Findings by kind

```dataview
TABLE WITHOUT ID item.kind AS "Kind", item.text AS "Finding", item.status AS "Status", file.link AS "Area"
FROM "diagnosis"
FLATTEN file.lists AS item
WHERE type = "area" AND item.kind AND item.status != "retired"
SORT item.kind, item.status
```
