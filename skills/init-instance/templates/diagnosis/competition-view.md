```dataview
TABLE segments, proposition, pricing, size, recent_move
FROM "diagnosis/competition"
WHERE type = "entity" AND relevance = "high" AND status != "archived"
SORT file.name
```

```dataview
TABLE relevance, status, review
FROM "diagnosis/competition"
WHERE type = "entity" AND (relevance != "high" OR status = "archived")
SORT status, file.name
```
