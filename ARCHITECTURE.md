# Agent Hub — Architecture

Copied from the "ARCHITECTURE.md" section of the v0.1 spec. This file is the
source of truth for structure; every agent working on the hub must follow it.
Lines marked *(added)* are not in the spec and were added when scaffolding.

One Python backend, one plain web frontend, one SQLite file, and project folders on disk.

> The spec has an embedded diagram here ("architecture · hub, agents, tools")
> that did not survive the export to markdown.

The router sends work either to an agent with a packed brief, or straight to a tool the hub can run with no agent at all.

## Stack

- Backend: Python 3.12, FastAPI, SQLite (via `sqlite3` or SQLModel), runs on `localhost`
- Frontend: plain HTML, CSS and a small amount of JS (htmx or Alpine.js). No React, no build step in v0.1
- Agents run as subprocesses; the hub never imports their code
- Target OS: Windows 11 first, Linux second

## The five concepts

| Concept | Stored as | Holds |
| --- | --- | --- |
| Project | Folder + `project.yaml` + DB row | Name, type, status, paths, notes, decisions |
| Project Type | `types/<name>.yaml` | Folders to create, default agents, tools, checklists |
| Agent | `adapters/<name>.py` | `available()`, `run()`, `usage()` |
| Task | DB row | Title, description, type, chosen agent, status |
| Run | DB row + `runs/<id>.md` in the project | Brief sent, output, diff, tokens if known, duration |

## Repo layout

```
agent-hub/
  ARCHITECTURE.md
  BUILD_PLAN.md      # (added) the v0.1 steps; "next step" = first unchecked one
  requirements.txt   # (added) Python dependencies
  pytest.ini         # (added) test settings
  data/              # (added) hub.db lives here; git-ignored, created on startup
  app/
    main.py          # FastAPI routes
    settings.py      # (added) loads config/settings.yaml, creates missing folders
    db.py            # SQLite schema + queries
    projects.py      # (added) loads types/*.yaml, creates and lists projects
    packer.py        # builds the brief for a task
    router.py        # reads routing.yaml + capabilities.yaml
    adapters/
      base.py        # the Adapter interface
      claude_code.py
      codex.py
  types/             # project type templates
    game.yaml
    utility.yaml
    3d-print.yaml
  themes/
    comfy.css
    hackers.css
  config/
    routing.yaml
    capabilities.yaml
    settings.yaml    # (added) projects_root, db_path, default_theme
  web/               # html, js
    templates/       # (added) Jinja2 templates rendered by FastAPI
      index.html     # the page shell
      _projects.html # project list + "New project" form; htmx swaps it
    vendor/
      htmx.min.js    # (added) htmx 2.0.4, vendored, no build step
    base.css         # (added) layout CSS; uses theme variables only
  tests/             # (added) pytest tests, one file per core module
```

*(added)* How the frontend is served: `app/main.py` renders
`web/templates/index.html` at `/`, mounts `web/` at `/static` and `themes/` at
`/themes`. The page links one theme file, chosen by `default_theme` in
`config/settings.yaml`; swapping that link swaps the theme.

## Database *(added)*

One SQLite file at `db_path`, created on startup by `app/db.py` (plain
`sqlite3`, foreign keys on). Timestamps are ISO 8601 text in UTC.

| Table | Columns |
| --- | --- |
| `projects` | `id`, `name` (unique), `type`, `status` (default `active`), `path` (unique), `created_at` |
| `tasks` | `id`, `project_id`, `title`, `description`, `type` (`code`, `review`, `docs`, `other`), `agent` (adapter name or `auto`), `status` (default `pending`), `created_at` |
| `runs` | `id`, `task_id`, `agent`, `started_at`, `finished_at`, `duration_s`, `exit_code`, `stdout`, `stderr`, `brief_path`, `diff`, `files_changed` (JSON list), `tokens_in`, `tokens_out` |
| `assets` | `id`, `project_id`, `path` (relative, unique per project), `type`, `size`, `tags` (comma-separated) |

A run row is inserted when the run starts, so its id exists for the snapshot
commit and `runs/<id>.md`; the result columns are filled in when it ends.
Deleting a project deletes its tasks, runs and assets rows (not its folder).

## Project folder layout (created from the type)

```
MyGame/
  project.yaml
  decisions.md       # one line per decision, newest first
  notes/
  assets/
  runs/              # one markdown file per run
  src/               # or whatever the type defines
```

*(added)* How a project is created (`app/projects.py`):

1. The name is checked: letters, digits, spaces, dashes and underscores only,
   starting with a letter or digit, 63 characters at most. The folder is
   `projects_root/<name>` and must not exist yet.
2. The type's `folders` are created, plus `notes/`, `assets/` and `runs/`
   for every type. Each empty folder gets a `.gitkeep` so git tracks it.
3. `project.yaml` is written with `name`, `type`, `status`, `created`,
   `goal`, `stack`, `conventions`. `decisions.md` starts empty (no heading,
   so the packer's "first 10 lines" are all decisions).
4. `git init`, then one commit: `hub: create project <name>`.
5. The `projects` row is inserted last.

Type templates are copied from the spec as-is. Agents and tools a template
names that v0.1 has no adapter for (`comfyui`, `ollama`, the 3d-print
`pipeline`) are stored but not used yet.

## Adapter interface (the only extension point in v0.1)

```python
class Adapter:
    name: str

    def available(self) -> bool:
        """Run `<cli> --version`; False if missing or failing."""

    def run(self, brief: str, workdir: Path) -> RunResult:
        """Send the brief headless, wait, return output + exit code."""
```

`usage()` is not part of the v0.1 interface; it comes back in v0.2 (decision 9).

```python
@dataclass
class RunResult:
    run_id: int
    agent: str
    task_id: int
    started_at: datetime
    finished_at: datetime
    duration_s: float
    exit_code: int
    stdout: str
    stderr: str
    brief_path: Path
    diff: str
    files_changed: list[str]
    tokens_in: int | None
    tokens_out: int | None
```

A new provider is one new file in `adapters/` plus one entry in `capabilities.yaml`. Nothing else changes.

## Context packer (where the token savings come from)

The brief is plain markdown, under a size budget set per agent:

1. Task title and description
2. Project summary from `project.yaml` (type, goal, stack, conventions)
3. First 10 lines of `decisions.md` (the file is newest-first; decision 8)
4. Contents of files the task names, or the asset index entries for them
5. Output rules: what to change, what not to touch, how to report back

The agent can still explore, but it starts already knowing the project.

## Themes

A theme is one CSS file that sets variables only: `--bg`, `--panel`, `--text`, `--muted`, `--accent`, `--font-ui`, `--font-mono`, `--radius`. The UI uses those variables and nothing else for colour and type. Hackers = black background, neon green/cyan, monospace, scanline overlay; Comfy = warm neutrals, rounded corners, a sans-serif UI font.

## Decisions

Made by Dan on 2026-11-16 in answer to open questions 7–15 from the Step 1
review. Where a decision conflicts with the spec, the decision wins.

7. **Settings.** `config/settings.yaml` holds `projects_root:
   ~/AgentHubProjects` (expanded with `pathlib`), `db_path: data/hub.db`
   (repo-relative, git-ignored) and `default_theme: comfy`. The UI can edit
   these. Missing folders are created on startup.
8. **Recent decisions.** Spec bug. `decisions.md` stays newest-first; the
   packer takes the **first** 10 lines.
9. **Adapter interface.** `usage()` is removed from the v0.1 interface and
   returns in v0.2. `RunResult` is a dataclass with: `run_id`, `agent`,
   `task_id`, `started_at`, `finished_at`, `duration_s`, `exit_code`,
   `stdout`, `stderr`, `brief_path`, `diff`, `files_changed: list[str]`,
   `tokens_in: int | None`, `tokens_out: int | None`.
10. **Routing precedence.** Agent set on the task > project type
    `default_agents[task_type]` > `routing.yaml`. `routing.yaml` only holds
    the global defaults and the fallback order. v0.1 task types: `code`,
    `review`, `docs`, `other`.
11. **Git per project.** The hub runs `git init` and makes an initial commit
    when it creates a project. Before each run: if the tree is dirty, commit
    `hub: snapshot before run <id>`. After the run, record the diff against
    that commit, then commit `hub: run <id> - <task title>`. Each run becomes
    one revertible commit.
12. **Git scope.** Local `git` only in v0.1, no `gh`.
13. **Brief budget.** In characters (about 4 chars per token), set per agent
    as `brief_budget_chars` in `capabilities.yaml`, default 24000. Over
    budget, cut in this order: file contents (largest first, replaced by
    their asset-index entry), then decisions down to 5 lines. Never cut the
    task or the output rules.
14. **Launching CLIs.** Resolve executables with `shutil.which` (it finds the
    `.cmd` shims). Pass args as a list, `shell=False`. Never pass the brief
    as a command-line argument. Send it via stdin if the CLI supports it;
    otherwise write it to `runs/<id>-brief.md` and pass a short prompt
    telling the agent to read that file.
15. **Frontend.** htmx, vendored at `web/vendor/htmx.min.js`, with Jinja2
    templates rendered by FastAPI. No Alpine unless a later step needs it.

## Usage gauges (v0.2 — not built in v0.1)

Themes change how usage looks; one fixed data shape keeps them all honest. The hub writes one `usage.json` per agent, and a gauge is a small JS file that draws it: `render(el, usage, theme)`. A theme picks which gauge goes in each slot, so new styles never touch the core.

```json
{
  "agent": "codex",
  "window": "5h",
  "tokens_used": 412000,
  "limit_estimate": 600000,
  "pct_used": 0.69,
  "burn_rate_per_hour": 95000,
  "est_cost_usd": 3.1,
  "confidence": "estimated",
  "updated": "2026-11-16T19:40:00+01:00"
}
```

A car dashboard maps cleanly onto the data, so use it as the default set:

| Gauge | Shows | Why it fits |
| --- | --- | --- |
| Speedometer | Burn rate (tokens per hour) | Rate is what a speedometer reads |
| Fuel gauge | Quota left in the current window | Empty means switch agents |
| Odometer | Total tokens this month | A running total |
| Warning light | Agent near its limit or unavailable | Triggers the router fallback |

Comfy renders these as soft dials and rings. Hackers renders the same data as terminal output: ASCII bars, a scrolling token ticker, a red `QUOTA CRITICAL` blink. Quota limits for subscriptions are estimates, so every gauge shows `confidence` and never pretends a guess is exact.
