```dataview
TABLE profile, criteria, willingness_to_pay, buying_process, channels, alternatives, size, served, basis
FROM "diagnosis/market"
WHERE type = "entity" AND relevance = "high" AND status != "archived"
SORT file.name
```

```dataview
TABLE relevance, status, review
FROM "diagnosis/market"
WHERE type = "entity" AND (relevance != "high" OR status = "archived")
SORT status, file.name
```
