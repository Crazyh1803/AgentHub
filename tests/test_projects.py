import subprocess
from contextlib import closing

import pytest
import yaml

from app.db import connect, init_db
from app.projects import ProjectError, create_project, list_projects, load_types
from app.settings import ROOT

TYPES = load_types(ROOT / "types")


@pytest.fixture
def conn(settings, git_identity):
    settings.projects_root.mkdir()
    with closing(connect(settings.db_path)) as conn:
        init_db(conn)
        yield conn


def git(folder, *args):
    result = subprocess.run(["git", *args], cwd=folder, capture_output=True, text=True)
    return result.stdout.strip()


def test_load_types_reads_the_three_templates():
    assert set(TYPES) == {"game", "utility", "3d-print"}
    assert TYPES["game"]["label"] == "Game"
    assert "scad" in TYPES["3d-print"]["folders"]


def test_game_project_gets_the_right_folders_and_files(conn, settings):
    folder = create_project(conn, settings.projects_root, TYPES["game"], "MyGame", "A small roguelike")

    assert folder == settings.projects_root / "MyGame"
    for sub in ("src", "assets/models", "assets/textures", "assets/audio", "notes", "runs"):
        assert (folder / sub).is_dir()
    assert (folder / "decisions.md").read_text(encoding="utf-8") == ""

    data = yaml.safe_load((folder / "project.yaml").read_text(encoding="utf-8"))
    assert data["name"] == "MyGame"
    assert data["type"] == "game"
    assert data["status"] == "active"
    assert data["goal"] == "A small roguelike"
    assert {"stack", "conventions", "created"} <= set(data)


def test_every_project_gets_notes_assets_and_runs(conn, settings):
    folder = create_project(conn, settings.projects_root, TYPES["3d-print"], "Bracket")
    for sub in ("scad", "stl", "gcode", "photos", "notes", "assets", "runs"):
        assert (folder / sub).is_dir()


def test_project_is_a_git_repo_with_one_clean_commit(conn, settings):
    folder = create_project(conn, settings.projects_root, TYPES["utility"], "Tool")
    assert git(folder, "log", "--format=%s") == "hub: create project Tool"
    assert git(folder, "status", "--porcelain") == ""
    tracked = git(folder, "ls-files").splitlines()
    assert "project.yaml" in tracked
    assert "src/.gitkeep" in tracked


def test_project_row_is_recorded(conn, settings):
    folder = create_project(conn, settings.projects_root, TYPES["game"], "  MyGame  ")
    (row,) = list_projects(conn)
    assert (row["name"], row["type"], row["status"]) == ("MyGame", "game", "active")
    assert row["path"] == str(folder)


def test_newest_project_is_listed_first(conn, settings):
    create_project(conn, settings.projects_root, TYPES["game"], "First")
    create_project(conn, settings.projects_root, TYPES["game"], "Second")
    assert [row["name"] for row in list_projects(conn)] == ["Second", "First"]


def test_existing_folder_is_rejected_and_left_alone(conn, settings):
    existing = settings.projects_root / "Taken"
    existing.mkdir()
    with pytest.raises(ProjectError, match="already exists"):
        create_project(conn, settings.projects_root, TYPES["game"], "Taken")
    assert list(existing.iterdir()) == []
    assert list_projects(conn) == []


@pytest.mark.parametrize("name", ["", "   ", "../escape", "a/b", "a\\b", "-dash", "bad:name", "x" * 64])
def test_unsafe_names_are_rejected(conn, settings, name):
    with pytest.raises(ProjectError, match="Name must"):
        create_project(conn, settings.projects_root, TYPES["game"], name)
    assert list(settings.projects_root.iterdir()) == []
