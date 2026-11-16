"""Claude Code adapter: `claude -p`, brief on stdin."""

from app.adapters.base import Adapter


class ClaudeCode(Adapter):
    name = "claude_code"
    executable = "claude"
    # -p prints the reply and exits, reading the prompt from stdin.
    # acceptEdits lets it edit files in the project without asking; shell
    # commands it would need approval for are refused, not run.
    run_args = ["-p", "--permission-mode", "acceptEdits"]
