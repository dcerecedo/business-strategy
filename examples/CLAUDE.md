# Examples

`acme/` is kept in git without its engine-owned files (`CLAUDE.md`, `_dashboard.md`, `.claude/rules/`, `scripts/`),
so they cannot drift from the templates.

If `acme/scripts/check.py` does not exist, stop and ask the user to run this from the repository root
before working in `acme/`:

```
python3 skills/init-instance/scaffold.py examples/acme --upgrade
```

Ask for the same command again after the user pulls a new version of the plugin.
