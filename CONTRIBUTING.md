# Contributing

## Goal

Keep `general-knowledge-base` focused, stable, and readable as a knowledge-vault framework.

Contributions should improve one of these areas:

- source digestion workflow
- source / topic / entity page contract
- thesis-mode writing workflow
- retrieval and audit quality
- documentation clarity

## Before You Change Anything

- Read [SKILL.md](./SKILL.md)
- Read [references/knowledge-schema.md](./references/knowledge-schema.md)
- Read [references/purpose-taxonomy.md](./references/purpose-taxonomy.md)
- If the change affects thesis mode, also read [references/thesis-mode.md](./references/thesis-mode.md)

## Core Rules

- Do not replace Codex-driven understanding with heuristic extraction logic.
- Keep `content.json` as the primary digestion input.
- Do not make `rebuild` rerun MinerU.
- Use explicit `UTF-8` for all Markdown and JSON reads/writes.
- Keep thesis working pages separate from digest-rendered source/topic/entity pages.

## Repository Change Guidelines

### Documentation changes

- Prefer concise, high-signal updates.
- Keep README oriented toward users and repository visitors.
- Keep `references/` focused on stable contracts and rules, not temporary notes.

### Script changes

- Preserve command-line stability unless there is a strong reason to break it.
- Add new commands only when they represent a stable workflow.
- Prefer explicit, readable logic over clever shortcuts.

### Thesis mode changes

- New thesis-mode pages or templates should be reusable across paper topics.
- Do not hard-code one specific thesis topic into the shared scaffolding.
- Changes should strengthen writing workflow structure, not turn the repo into a one-off project dump.

## Testing Checklist

Before submitting a change, verify:

- the script still parses with Python
- new commands run successfully when applicable
- README examples still match actual command names
- UTF-8 Markdown renders correctly on Windows

## Commit Style

Prefer short, descriptive commit messages, for example:

- `Add thesis knowledge base mode`
- `Polish README for thesis mode release`
- `Document UTF-8 handling for Windows`

## Release Notes

When preparing a release, write release notes around the current version's value.

- Describe what this version adds
- Keep the message clear and user-facing
- Avoid turning the release page into a long comparison against older versions unless that comparison is genuinely necessary
