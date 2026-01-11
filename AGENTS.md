# Agent Guidelines

This document captures preferences for AI agents (Claude, etc.) working on this codebase.

## Commit Messages

- Use prefixes: `add:`, `fix:`, `update:`, `remove:`
- Keep titles lowercase where possible
- Titles are sentence fragments (no trailing period)
- Use backticks for code references in titles (e.g., `fix: bug in \`keep_going\` parsing`)
- Reference issue numbers with `(#123)` or `(closes #123)`
- Include `Co-Authored-By: {Model Name} <noreply@anthropic.com>` in commit body

Example:
```
fix: walrus operator precedence bug in `keep_going` parsing (closes #96)

Description of the fix.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## GitHub Issues

- Use same prefix convention as commits: `add:`, `fix:`, `update:`
- Keep titles lowercase where possible
- Use backticks for code references in titles
- Add `aigen` label for AI-generated issues
- Include "Created by {Model Name} during code review" at end of issue body

## Development Commands

- **Run tests**: `ds test` (not raw pytest)
- **Sync dependencies**: `uv sync` or `uv sync --all-extras`
- **Run with local changes**: `uv run ds <args>`
- **Install package**: handled by `uv sync`, not `pip install -e .`

## Shell Commands

- Use `fd` instead of `find` (simpler syntax, respects `.gitignore`)
- Use `rg` instead of `grep` (faster, better defaults)

## Code Style

- Follow existing patterns in the codebase
- Use type hints (modern syntax: `Path | None` not `Optional[Path]`)
- Prefer editing existing files over creating new ones
- Don't add unnecessary comments or docstrings to unchanged code
