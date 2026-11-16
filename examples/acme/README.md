# Acme example

Fictional instance to try `scripts/check.py`. Company, sources and figures are invented.

Its engine-owned files (`CLAUDE.md`, `.claude/rules/`, `scripts/`) are not in git. Generate them
from the repository root, and again after each plugin update:

```
python3 skills/init-instance/scaffold.py examples/acme --upgrade
```

Then, from `examples/acme` with PyYAML available (see `requirements.txt`):

```
python3 scripts/check.py . --today 2026-11-15
```

Seeded: an expired source, a contradicted claim, a hypothesis past its deadline, and an expired
source that no decision relies on. The first three must reach D-001, direction and OKR-2027; the
last must show up as an archive candidate.
