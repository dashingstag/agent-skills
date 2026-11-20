# agent-skills

Personal skills for [Devin CLI](https://devin.ai) and compatible agent sessions.

## Install

```bash
devin plugins install dashingstag/agent-skills
```

This installs every skill under `skills/` as `/<plugin>:<skill>` slash commands.

## Skills

| Skill | Purpose |
|---|---|
| `hapiv` | Implement a change while verification runs as parallel asynchronous jobs on whatever execution harness is available, then repair failures and aggregate one evidence-backed verdict (Harness-Agnostic Parallel Implementation and Verification). |

## Layout

```
skills/<name>/SKILL.md   # one directory per skill
.devin-plugin/plugin.json # plugin manifest
```

New skills go in their own `skills/<name>/` directory following the
[SKILL.md format](https://docs.devin.ai/cli/extensibility/skills/creating-skills).
