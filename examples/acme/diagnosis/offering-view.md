```dataview
TABLE segments, proposition, pricing, stage
FROM "diagnosis/offering"
WHERE type = "entity" AND relevance = "high" AND status != "archived"
SORT file.name
```

```dataview
TABLE relevance, status, review
FROM "diagnosis/offering"
WHERE type = "entity" AND (relevance != "high" OR status = "archived")
SORT status, file.name
```
