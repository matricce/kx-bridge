# KX-Bridge Claude Agents

## Available Agents

| Agent | File | When to use |
|---|---|---|
| Reviewer | `.claude/agents/reviewer.md` | Before every PR — checks logic, error handling, Moonraker compatibility |
| Changelog | `.claude/agents/changelog.md` | After merge to nightly — generates CHANGELOG.md entry from commits |
| Test Writer | `.claude/agents/test-writer.md` | When adding new functions — derives pytest tests |
| Nightly Prep | `.claude/agents/nightly-prep.md` | Before a release — checks readiness of nightly → main merge |
| Docker Check | `.claude/agents/docker-check.md` | Before image push — validates Dockerfile and compose config |
| Moonraker Debug | `.claude/agents/moonraker-debug.md` | On runtime errors — analyzes Moonraker/Klipper logs |

## Usage

In VS Code with Claude Code extension:
```
@reviewer     → code review of current changes
@changelog    → generate CHANGELOG entry
@test-writer  → write tests for changed files
@nightly-prep → check release readiness
@docker-check → validate Docker config
@moonraker-debug → analyze logs
```

## Context

- Moonraker API: Port 7125
- AFC lane_data: flat indexing lane1–lane4
- Registry: `gitea.it-drui.de/viewit/kx-bridge`
- Default PR target: `nightly`
