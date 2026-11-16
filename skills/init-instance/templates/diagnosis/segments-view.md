```dataview
TABLE served, relevance, size, basis
FROM "diagnosis/market"
WHERE type = "entity" AND status != "archived"
SORT served DESC, relevance, file.name
```

```dataview
TABLE segment, job, current_alternative
FROM "conclusions"
WHERE framework = "jtbd" AND status = "current"
SORT segment
```
