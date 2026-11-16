# Build plan, v0.1

- [x] 1. Scaffold: repo layout, venv, FastAPI serving a blank page
       with the Comfy theme
- [x] 2. Settings + database: load config/settings.yaml; SQLite
       schema for projects, tasks, runs, assets; tests
- [x] 3. Projects: load types/*.yaml (game, utility, 3d-print);
       create a project (folders, project.yaml, decisions.md,
       git init + first commit); UI: project list + "New project"
       form
- [ ] 4. Asset index: scan a project folder into the assets table;
       show it on the project page with a Rescan button
- [ ] 5. Adapters: base.py, claude_code.py, codex.py; available()
       health check shown in the UI header; run() with stdin or
       brief file, tested with a trivial prompt
- [ ] 6. Context packer: build the brief within budget; UI shows a
       preview of the brief before sending
- [ ] 7. Router: precedence rules + fallback when an agent is
       unavailable; tests
- [ ] 8. Tasks + runs: task form; run in the background with htmx
       status polling; git snapshot, diff, commit;
       runs/<id>.md; run log page
- [ ] 9. Hackers theme + theme switcher saved to settings
- [ ] 10. Walk through every done criterion in SPEC.md, fix the
        gaps, update ARCHITECTURE.md and write a README
