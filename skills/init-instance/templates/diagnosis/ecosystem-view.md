```dataview
TABLE role, dependency, alternatives
FROM "diagnosis/ecosystem"
WHERE type = "entity" AND relevance = "high" AND status != "archived"
SORT file.name
```

```dataview
TABLE relevance, status, review
FROM "diagnosis/ecosystem"
WHERE type = "entity" AND (relevance != "high" OR status = "archived")
SORT status, file.name
```
