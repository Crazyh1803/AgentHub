# Agent Hub — v0.1 Spec

Nov 16, 2026 · @Daniel Whitcomb

## Purpose and principles

Agent Hub is a local app that keeps every project's memory in one place and hands each task to the cheapest agent or tool that can do it well. It saves tokens by doing the deterministic work itself (files, git, context packing, tool calls) before any paid agent gets involved.

**What it is:** a project manager, a context packer, a router and a run log.

**What it is not:** a chat client, an IDE, a replacement for Codex or Claude Code, or a middleman for tool connections. Agents connect to Blender, ComfyUI and OpenSCAD themselves; the hub only writes their config.

**Rules that keep it simple**

1. Five concepts only: Project, Project Type, Agent, Task, Run. A new feature that needs a sixth concept needs a written reason.
2. Plain files first. Anything an agent might need to read lives as a file in the project folder, not only in the database.
3. Every module is deletable. Removing an adapter or a theme never breaks the core.
4. No v0.2 work until v0.1 has been used daily for two weeks.
5. Prefer existing tools (ccusage, MCP servers, slicer CLIs) over writing our own.
6. Route order for any service: API or CLI, then MCP, then browser automation as a last resort.
7. Never automate the consumer chat web apps (claude.ai, ChatGPT). Official CLIs and APIs only.

## v0.1 scope

v0.1 is done when Dan can create a project, send a task to Claude Code or Codex with packed context, and see the run logged, without opening a terminal.

**In v0.1**

- Create, list and open projects from a Project Type template
- Project folder with `project.yaml`, `notes/`, `assets/`, `decisions.md`
- Asset index: scan the folder, record path, type, size and tags in SQLite
- Task form: title, description, type, target agent (or "auto")
- Context packer: builds the brief from the task, the project's `project.yaml`, recent decisions and the files the task names
- Two adapters: Claude Code (`claude -p`) and Codex CLI (`codex exec`)
- Run log: prompt sent, output, files changed (git diff), duration, exit code
- Simple routing: a rule table in `routing.yaml` (task type to agent, with a fallback)
- Startup health check: each adapter's `available()` runs `--version`
- Two themes: Comfy (default) and Hackers

**Out of v0.1**

- Usage tracking and quota-aware routing (v0.2)
- Local Qwen/Ollama worker (v0.2)
- Gemini, Grok, Blender, ComfyUI, OpenSCAD, printer adapters (v0.3)
- Local AI installer wizard, MCP server, theme sharing (later)
- Multi-user, cloud sync, auth

**Done criteria**

- [ ] A new project from the `game` type creates the right folders and `project.yaml`
- [ ] A task sent to Claude Code completes and its run appears in the log with the git diff
- [ ] The same task sent to Codex works through the same form
- [ ] Unplugging one CLI shows it as unavailable and routing falls back
- [ ] Switching to the Hackers theme changes the whole UI with no reload errors
- [ ] `ARCHITECTURE.md` matches the code

## ARCHITECTURE.md

One Python backend, one plain web frontend, one SQLite file, and project folders on disk. Copy this section into the repo as `ARCHITECTURE.md`; every agent working on the hub must follow it.

&#91;embedded content: architecture · hub, agents, tools\]

The router sends work either to an agent with a packed brief, or straight to a tool the hub can run with no agent at all.

**Stack**

- Backend: Python 3.12, FastAPI, SQLite (via `sqlite3` or SQLModel), runs on `localhost`
- Frontend: plain HTML, CSS and a small amount of JS (htmx or Alpine.js). No React, no build step in v0.1
- Agents run as subprocesses; the hub never imports their code
- Target OS: Windows 11 first, Linux second

**The five concepts**

| Concept | Stored as | Holds |
| --- | --- | --- |
| Project | Folder + `project.yaml` + DB row | Name, type, status, paths, notes, decisions |
| Project Type | `types/<name>.yaml` | Folders to create, default agents, tools, checklists |
| Agent | `adapters/<name>.py` | `available()`, `run()`, `usage()` |
| Task | DB row | Title, description, type, chosen agent, status |
| Run | DB row + `runs/<id>.md` in the project | Brief sent, output, diff, tokens if known, duration |

**Repo layout**

```
agent-hub/
  ARCHITECTURE.md
  app/
    main.py          # FastAPI routes
    db.py            # SQLite schema + queries
    packer.py        # builds the brief for a task
    router.py        # reads routing.yaml + capabilities.yaml
    adapters/
      base.py        # the Adapter interface
      claude_code.py
      codex.py
  types/             # project type templates
  themes/
    comfy.css
    hackers.css
  config/
    routing.yaml
    capabilities.yaml
  web/               # html, js
```

**Project folder layout** (created from the type)

```
MyGame/
  project.yaml
  decisions.md       # one line per decision, newest first
  notes/
  assets/
  runs/              # one markdown file per run
  src/               # or whatever the type defines
```

**Adapter interface** (the only extension point in v0.1)

```python
class Adapter:
    name: str

    def available(self) -> bool:
        """Run `<cli> --version`; False if missing or failing."""

    def run(self, brief: str, workdir: Path) -> RunResult:
        """Send the brief headless, wait, return output + exit code."""

    def usage(self) -> Usage | None:
        """v0.2: read local logs. Return None if unknown."""
```

A new provider is one new file in `adapters/` plus one entry in `capabilities.yaml`. Nothing else changes.

**Context packer** (where the token savings come from)

The brief is plain markdown, under a size budget set per agent:

1. Task title and description
2. Project summary from `project.yaml` (type, goal, stack, conventions)
3. Last 10 lines of `decisions.md`
4. Contents of files the task names, or the asset index entries for them
5. Output rules: what to change, what not to touch, how to report back

The agent can still explore, but it starts already knowing the project.

**Themes**

A theme is one CSS file that sets variables only: `--bg`, `--panel`, `--text`, `--muted`, `--accent`, `--font-ui`, `--font-mono`, `--radius`. The UI uses those variables and nothing else for colour and type. Hackers = black background, neon green/cyan, monospace, scanline overlay; Comfy = warm neutrals, rounded corners, a sans-serif UI font.

**Usage gauges** (v0.2)

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

## Project types

A project type is a YAML template, not AI judgement: it tells the hub what folders to make, which agents and tools fit, and what "done" looks like. A new kind of project is a new file; an agent can draft one from a short description.

```yaml
# types/game.yaml
name: game
label: Game
folders: [src, assets/models, assets/textures, assets/audio, notes, runs]
default_agents:
  code: codex
  review: claude_code
  assets_3d: claude_code      # drives Blender via MCP
  images: comfyui
  cheap: ollama
tools: [git, blender, comfyui]
checklist:
  - Game design doc in notes/
  - Playable build runs
  - Assets indexed
```

```yaml
# types/utility.yaml
name: utility
label: Utility app
folders: [src, tests, notes, runs]
default_agents:
  code: codex
  review: claude_code
  cheap: ollama
tools: [git]
checklist:
  - README with install steps
  - Tests pass
```

```yaml
# types/3d-print.yaml
name: 3d-print
label: 3D print
folders: [scad, stl, gcode, photos, notes, runs]
default_agents:
  model: claude_code          # writes .scad
  cheap: ollama
tools: [openscad, orcaslicer, printer]
pipeline:                      # deterministic, no agent tokens
  - openscad: scad/*.scad -> stl/
  - slicer:   stl/*.stl -> gcode/ (profile: config/creality.ini)
  - printer:  upload gcode, do not auto-start
checklist:
  - Parameters exposed at top of .scad
  - Preview PNG rendered
  - Test print logged with photo
```

The 3D-print type shows the core idea: an agent writes the parametric `.scad` once, then the hub renders, slices and uploads with plain CLI calls. Changing a dimension costs zero tokens.

## capabilities.yaml

Every service the hub can reach, and how, lives in one file the router reads. Route order is always API/CLI, then MCP, then browser. CLI flags and MCP servers change fast, so the hub checks each entry at startup instead of trusting this table.

| Service | Best route | Fallback | Cost | Phase |
| --- | --- | --- | --- | --- |
| Claude Code | CLI `claude -p` | — | Subscription (Pro) | v0.1 |
| Codex | CLI `codex exec` | — | Subscription | v0.1 |
| Git / GitHub | `git` + `gh` CLI | GitHub MCP server | Free | v0.1 |
| Ollama (local Qwen) | REST API `localhost:11434` | `ollama run` CLI | Free | v0.2 |
| Usage stats | ccusage (reads local logs) | Own parser of `~/.claude/projects` and `~/.codex/sessions` | Free | v0.2 |
| Gemini | Gemini CLI | Gemini API | Subscription (Google AI Pro) | v0.3 |
| Grok | xAI API | Browser | Per-token | v0.3 |
| OpenSCAD | CLI `openscad -o out.stl -D w=40 part.scad` | OpenSCAD MCP server | Free | v0.3 |
| Slicer | PrusaSlicer CLI `--export-gcode` | OrcaSlicer CLI | Free | v0.3 |
| Creality printer | Moonraker REST API, port 7125 | Manual upload | Free | v0.3 (see next section) |
| Blender | CLI `blender --background --python x.py` | BlenderMCP add-on | Free | v0.3 |
| ComfyUI | HTTP API `localhost:8188` (API-format workflow JSON) | ComfyUI MCP server | Free | v0.3 |
| Any website | Playwright script (no AI) | Playwright MCP driven by an agent | Free | Later |
| claude.ai / ChatGPT web | Not automated | Manual export | — | Never |

**Entry format**

```yaml
openscad:
  route: cli
  command: openscad
  check: openscad --version
  fallback: mcp:openscad
  auth: none
  cost: free
  can_drive: [hub, claude_code, codex]   # hub = runs with no agent at all
  good_for: [render_stl, render_png, set_parameters]

codex:
  route: cli
  command: codex exec
  check: codex --version
  auth: chatgpt-login
  cost: subscription
  usage_source: ~/.codex/sessions
  good_for: [code, refactor, tests]
```

`can_drive: [hub]` is the important flag: anything the hub can run itself never touches an agent's quota.

## Creality printer

Yes, a Creality printer can work with the hub, but the route depends on the model. Most current Creality machines run Klipper, and the hub talks to Klipper through the Moonraker API.

| Model family | What's on it | Route for the hub |
| --- | --- | --- |
| K2 series | Klipper + Moonraker built in | Moonraker on port 7125, nothing to install ([Printago](https://docs.printago.io/docs/connecting-printers/creality)) |
| K1 / K1 Max / K1C, Ender-3 V3 / KE | Klipper, Moonraker not included by default | Enable root (an official option), install Moonraker with the community helper script, then port 7125 ([FlowQ guide](https://infinityflow3d.com/blogs/flowq-printer-connection-guides/creality-k1-ender-3-v3-series-connection-guide-flowq), [SimplyPrint](https://simplyprint.io/setup-guide/creality/k1-max.md)) |
| K1C 2025 revision | Moonraker-compatible API on 7125 works; root removed | Use the API on 7125 directly ([Creality forum](https://forum.creality.com/t/k1c-2025-orcaslicer-workarounds-for-missing-web-interface/47164)) |
| Older Ender (Marlin firmware, e.g. Ender-3 V2 / S1) | No network API | Add a Raspberry Pi running OctoPrint (REST API), or keep it manual: hub drops G-code on the SD card or a shared folder |

**What the hub does with it (v0.3)**

- Upload G-code and show printer state, temperatures and progress
- Never start a print automatically: a human confirms on the printer or in the UI
- Log each print to the project's `runs/` with the settings used

Rooting may void the warranty; read Creality's terms for your model first.

**Your printer:** Dan's printer is a K1 SE. Route: enable root from the touchscreen, install Moonraker with the Guilouz helper script, then connect on port 7125 (\[SimplyPrint K1 SE guide\](https://simplyprint.io/setup-guide/creality/k1-se/on-printer))

## Existing tools on GitHub

Reuse the integrations, borrow ideas from the orchestrators, and build only the part nobody else has: project memory, project types, and non-code pipelines like 3D printing.

**Use directly (dependencies)**

| Tool | What it gives the hub | Phase |
| --- | --- | --- |
| [ccusage](https://github.com/ryoppippi/ccusage) | Token and cost reports from local logs for Claude Code, Codex, Gemini CLI and more; no network calls | v0.2 |
| [blender-mcp](https://github.com/ahujasid/blender-mcp) | Lets Claude Code or Codex drive Blender; includes an arbitrary-code tool, so keep it local | v0.3 |
| [openscad-mcp (quellant)](https://glama.ai/mcp/servers/quellant/openscad-mcp) | Render, export and analyse OpenSCAD models from an agent; one-line `claude mcp add` | v0.3 |
| [comfyui-mcp-server (joenorton)](https://awesome.ecosyste.ms/projects/github.com%2Fjoenorton%2Fcomfyui-mcp-server) | Lightweight Python MCP server for a local ComfyUI | v0.3 |
| Moonraker API ([docs](https://moonraker.readthedocs.io/en/latest/external_api/printer/)) | Printer state and control over HTTP | v0.3 |

**Read, don't adopt (orchestrators)**

These already run Claude Code, Codex and Gemini CLI side by side. They focus on parallel coding in git worktrees, not project memory or Blender and printer pipelines, so adopting one would bend the hub around their model.

| Project | Why look at it |
| --- | --- |
| [mco](https://awesome.ecosyste.ms/projects/github.com%2Fmco-org%2Fmco) | Small Python layer that dispatches to Claude Code, Codex CLI, Gemini CLI and Qwen Code. Closest to our adapter design. |
| [CLI Agent Orchestrator (AWS)](https://github.blesdmm.dns-dynamic.net/awslabs/cli-agent-orchestrator) | Supervisor/worker patterns across many coding CLIs |
| [agent-orchestrator](https://awesome.ecosyste.ms/projects/github.com%2FAgentWrapper%2Fagent-orchestrator) | Most popular of the group (about 7.7k stars); worth trying as-is if you only want parallel coding agents |
| [Coral](https://github.com/cdknorow/coral/wiki) | Browser board view of agents as one team; useful UI reference |

Before writing the Claude Code and Codex adapters, ask Codex to read mco's adapter code and summarise how it calls each CLI. That costs a few thousand tokens and saves days.

## Roadmap and open questions

Ship the core first, then the token savings, then the creative and printing tools. v0.1 is highlighted because it is the only phase being built now.

&#91;embedded content: roadmap · 4 phases, 3 gates\]

**Open questions**

- [ ] Root the K1 SE and install Moonraker (see Creality printer section)
- [ ] Does your Google AI Pro plan include Gemini CLI quota, and how much?
- [ ] Grok: worth paying per token, or drop it until there's a clear job for it?
- [ ] Name for the app ("Agent Hub" is a placeholder)
- [ ] Open source it from day one, or keep it private until v0.3?
