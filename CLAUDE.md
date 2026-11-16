# Agent Hub — rules for agents working in this repo

Read `SPEC.md` before starting any task. `ARCHITECTURE.md` is the source of truth for structure; if code and that file disagree, stop and ask.

## Scope
- Build v0.1 only (see "v0.1 scope" in SPEC.md). Anything listed under "Out of v0.1" is out, even if it seems easy.
- Five concepts only: Project, Project Type, Agent, Task, Run. Do not add a sixth without asking.

## Stack (do not change without asking)
- Python 3.12, FastAPI, SQLite
- Plain HTML/CSS + htmx or Alpine.js. No React, no build step.
- Agents run as subprocesses (`claude -p`, `codex exec`). Never import their code.
- Windows 11 first: use `pathlib`, no hardcoded paths, no bash-only scripts.

## Rules
- No hardcoded paths, accounts or keys. Everything goes in `config/`.
- Every module must be deletable without breaking the core.
- Themes are CSS-variable files only. UI code uses the variables, never raw colours.
- Keep files small and readable. Prefer boring code over clever code.
- Write a short test for each piece of core logic (packer, router, project creation).
- Update `ARCHITECTURE.md` in the same change as any structural change.

## Working style
- Work in small steps. After each step: run the tests, show what changed, and stop for review.
- If a requirement is unclear, ask instead of guessing.
