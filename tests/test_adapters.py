"""Adapter tests use the Python interpreter as a stand-in CLI, so they need
neither claude nor codex installed and spend no quota."""

import sys

from app.adapters import check_health, load_adapters
from app.adapters.base import EXIT_NOT_FOUND, EXIT_TIMED_OUT, Adapter

ECHO = (
    "import os, sys\n"
    "brief = sys.stdin.read()\n"
    "print(len(brief))\n"
    "print(os.getcwd())\n"
    "print(len(sys.argv))\n"
    "sys.stderr.write('a warning')\n"
    "sys.exit(3)\n"
)


class Fake(Adapter):
    name = "fake"
    executable = sys.executable
    run_args = ["-c", ECHO]


class Missing(Adapter):
    name = "missing"
    executable = "no-such-cli-on-this-machine"
    run_args = []


def test_available_when_version_command_succeeds():
    assert Fake().available() is True


def test_unavailable_when_cli_is_missing():
    assert Missing().available() is False


def test_unavailable_when_version_command_fails():
    broken = Fake()
    broken.version_args = ["-c", "import sys; sys.exit(1)"]
    assert broken.available() is False


def test_run_sends_brief_on_stdin_and_reports_the_outcome(tmp_path):
    brief = "x" * 100_000   # far longer than a Windows command line allows
    result = Fake().run(brief, tmp_path)

    length, cwd, argc = result.stdout.split()
    assert int(length) == 100_000
    assert cwd == str(tmp_path)
    assert int(argc) == 1          # the brief is not among the arguments
    assert result.stderr == "a warning"
    assert result.exit_code == 3
    assert result.agent == "fake"
    assert result.finished_at >= result.started_at
    assert result.duration_s >= 0
    assert (result.run_id, result.task_id, result.tokens_in) == (None, None, None)


def test_run_reports_a_missing_cli_instead_of_raising(tmp_path):
    result = Missing().run("hello", tmp_path)
    assert result.exit_code == EXIT_NOT_FOUND
    assert "not found" in result.stderr


def test_run_stops_at_the_timeout(tmp_path):
    slow = Fake()
    slow.run_args = ["-c", "import time; time.sleep(30)"]
    slow.run_timeout_s = 1
    result = slow.run("hello", tmp_path)
    assert result.exit_code == EXIT_TIMED_OUT
    assert "Timed out" in result.stderr
    assert result.duration_s < 20


def test_load_adapters_finds_both_providers():
    adapters = load_adapters()
    assert list(adapters) == ["claude_code", "codex"]
    assert adapters["claude_code"].executable == "claude"
    assert adapters["claude_code"].run_args[0] == "-p"
    assert adapters["codex"].run_args[0] == "exec"


def test_check_health_reports_each_adapter():
    assert check_health({"fake": Fake(), "missing": Missing()}) == {"fake": True, "missing": False}
