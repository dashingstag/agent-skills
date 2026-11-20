# agent-skills

Personal skill library for Devin, Claude Code, Codex and GitHub Copilot.

## Canonical layout

- `skills/<name>/SKILL.md` — the source of truth for every skill. Edit here only.
- `.agents/skills/`, `.claude/skills/`, `.github/skills/` — generated discovery
  copies. Never edit them directly; run the sync script instead.
- `.devin-plugin/plugin.json` — Devin plugin manifest.
- `.claude-plugin/plugin.json` + `marketplace.json` — Claude plugin and
  marketplace manifests so the repo installs with one command.

## Add or change a skill

1. Edit `skills/<name>/SKILL.md` (new skill: new directory, kebab-case name
   matching the `name:` frontmatter).
2. Run `python tools/sync_skills.py` to refresh the discovery copies.
3. Commit the skill directory and the refreshed copies together.
4. `python tools/sync_skills.py --check` verifies copies are current.

## Publish to personal skill folders

`python tools/sync_skills.py --install` copies skills into
`~/.agents/skills`, `~/.claude/skills`, `~/.codex/skills` and
`~/.copilot/skills`. Only directories carrying this repo's
`.agent-skills-managed` marker are pruned, so skills installed by other
tools are left alone.
