"""The Adapter interface (see ARCHITECTURE.md).

A provider is one subclass in its own file that sets `name`, `executable` and
`run_args`. The brief always goes to the CLI on stdin, never as an argument.
"""

import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

EXIT_TIMED_OUT = 124
EXIT_NOT_FOUND = 127


@dataclass(kw_only=True)
class RunResult:
    """What one run produced. The adapter fills in what it knows; the hub
    adds the rest (ids, brief path, diff) when it records the run."""

    run_id: int | None = None
    agent: str
    task_id: int | None = None
    started_at: datetime
    finished_at: datetime
    duration_s: float
    exit_code: int
    stdout: str
    stderr: str
    brief_path: Path | None = None
    diff: str = ""
    files_changed: list[str] = field(default_factory=list)
    tokens_in: int | None = None
    tokens_out: int | None = None


class Adapter:
    name: str
    executable: str                 # looked up on PATH with shutil.which
    run_args: list[str]             # flags for a headless run that reads stdin
    version_args: list[str] = ["--version"]
    version_timeout_s: float = 30
    run_timeout_s: float = 1800

    def available(self) -> bool:
        """Run `<cli> --version`; False if missing or failing."""
        exe = shutil.which(self.executable)
        if exe is None:
            return False
        try:
            result = subprocess.run(
                [exe, *self.version_args],
                capture_output=True,
                timeout=self.version_timeout_s,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return result.returncode == 0

    def run(self, brief: str, workdir: Path) -> RunResult:
        """Send the brief headless on stdin, wait, return output + exit code."""
        started = datetime.now(timezone.utc)
        exe = shutil.which(self.executable)
        if exe is None:
            return self._result(started, EXIT_NOT_FOUND, "", f"{self.executable} was not found on PATH")
        try:
            done = subprocess.run(
                [exe, *self.run_args],
                input=brief,
                cwd=workdir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.run_timeout_s,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", "replace") if exc.stdout else ""
            return self._result(started, EXIT_TIMED_OUT, stdout, f"Timed out after {self.run_timeout_s} s")
        except OSError as exc:
            return self._result(started, EXIT_NOT_FOUND, "", f"Could not start {self.executable}: {exc}")
        return self._result(started, done.returncode, done.stdout, done.stderr)

    def _result(self, started: datetime, exit_code: int, stdout: str, stderr: str) -> RunResult:
        finished = datetime.now(timezone.utc)
        return RunResult(
            agent=self.name,
            started_at=started,
            finished_at=finished,
            duration_s=round((finished - started).total_seconds(), 3),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
        )
