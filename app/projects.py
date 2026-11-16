"""Project types and project creation."""

import re
import shutil
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Every project gets these, whatever its type defines.
ALWAYS_FOLDERS = ("notes", "assets", "runs")

# Letters, digits, spaces, dashes and underscores: safe as a Windows folder name.
NAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,62}")


class ProjectError(Exception):
    """A project could not be created; the message is shown to the user."""


def load_types(types_dir: Path) -> dict[str, dict]:
    """Read every types/*.yaml, keyed by the type's name."""
    types = {}
    for path in sorted(types_dir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        types[data["name"]] = data
    return types


def list_projects(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM projects ORDER BY id DESC").fetchall()


def create_project(
    conn: sqlite3.Connection,
    projects_root: Path,
    project_type: dict,
    name: str,
    goal: str = "",
) -> Path:
    """Create the folder, files, git repo and DB row. Returns the folder."""
    name = name.strip()
    if not NAME_PATTERN.fullmatch(name):
        raise ProjectError(
            "Name must start with a letter or digit and use only letters, "
            "digits, spaces, dashes and underscores (63 characters at most)."
        )
    folder = projects_root / name
    if folder.exists():
        raise ProjectError(f"A folder named '{name}' already exists in {projects_root}.")
    git = shutil.which("git")
    if git is None:
        raise ProjectError("git was not found on PATH; it is needed to create a project.")

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    folder.mkdir(parents=True)
    for sub in dict.fromkeys([*project_type.get("folders", []), *ALWAYS_FOLDERS]):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    _keep_empty_folders(folder)
    _write_project_yaml(folder, name, project_type["name"], goal.strip(), created_at)
    (folder / "decisions.md").write_text("", encoding="utf-8")

    _git(git, folder, "init")
    _git(git, folder, "add", "-A")
    _git(git, folder, "commit", "-m", f"hub: create project {name}")

    conn.execute(
        "INSERT INTO projects (name, type, path, created_at) VALUES (?, ?, ?, ?)",
        (name, project_type["name"], str(folder), created_at),
    )
    conn.commit()
    return folder


def _write_project_yaml(folder: Path, name: str, type_name: str, goal: str, created_at: str) -> None:
    data = {
        "name": name,
        "type": type_name,
        "status": "active",
        "created": created_at,
        "goal": goal,
        "stack": "",
        "conventions": "",
    }
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    (folder / "project.yaml").write_text(text, encoding="utf-8")


def _keep_empty_folders(folder: Path) -> None:
    """Git does not track empty folders, so give each one a .gitkeep."""
    for path in folder.rglob("*"):
        if path.is_dir() and not any(path.iterdir()):
            (path / ".gitkeep").write_text("", encoding="utf-8")


def _git(git: str, folder: Path, *args: str) -> None:
    result = subprocess.run(
        [git, *args], cwd=folder, capture_output=True, text=True, shell=False
    )
    if result.returncode != 0:
        raise ProjectError(
            f"git {args[0]} failed in {folder}: {result.stderr.strip()}"
        )
