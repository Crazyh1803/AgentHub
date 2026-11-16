"""Codex CLI adapter: `codex exec`, brief on stdin."""

from app.adapters.base import Adapter


class Codex(Adapter):
    name = "codex"
    executable = "codex"
    # The trailing "-" tells `codex exec` to read the prompt from stdin.
    # --full-auto lets it edit files inside the project folder, sandboxed.
    run_args = ["exec", "--full-auto", "-"]
