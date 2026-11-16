from contextlib import closing
from pathlib import Path

import pytest

from app.assets import asset_type, list_assets, scan_project
from app.db import connect, init_db


@pytest.fixture
def conn(settings):
    with closing(connect(settings.db_path)) as conn:
        init_db(conn)
        yield conn


def add_project(conn, folder: Path) -> int:
    folder.mkdir(parents=True)
    return conn.execute(
        "INSERT INTO projects (name, type, path, created_at) VALUES (?, ?, ?, ?)",
        (folder.name, "game", str(folder), "2026-11-16T12:00:00+00:00"),
    ).lastrowid


def write(folder: Path, relative: str, content: str = "x") -> None:
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def paths(conn, project_id):
    return [row["path"] for row in list_assets(conn, project_id)]


def test_asset_type_comes_from_the_extension():
    assert asset_type(Path("logo.PNG")) == "image"
    assert asset_type(Path("part.scad")) == "model"
    assert asset_type(Path("main.py")) == "code"
    assert asset_type(Path("notes.md")) == "doc"
    assert asset_type(Path("mystery.xyz")) == "other"
    assert asset_type(Path("Makefile")) == "other"


def test_scan_records_path_type_size_and_tags(conn, tmp_path):
    folder = tmp_path / "MyGame"
    project_id = add_project(conn, folder)
    write(folder, "project.yaml", "name: MyGame")
    write(folder, "assets/textures/wall.png", "12345")

    assert scan_project(conn, project_id, folder) == 2

    texture, config = list_assets(conn, project_id)
    assert (config["path"], config["type"], config["size"]) == ("project.yaml", "data", 12)
    assert config["tags"] == ""
    assert (texture["path"], texture["type"], texture["size"]) == ("assets/textures/wall.png", "image", 5)
    assert texture["tags"] == "assets,textures"


def test_scan_skips_hidden_files_and_folders(conn, tmp_path):
    folder = tmp_path / "MyGame"
    project_id = add_project(conn, folder)
    write(folder, ".git/config")
    write(folder, "notes/.gitkeep", "")
    write(folder, ".env")
    write(folder, "notes/idea.md")

    scan_project(conn, project_id, folder)
    assert paths(conn, project_id) == ["notes/idea.md"]


def test_rescan_adds_updates_and_removes(conn, tmp_path):
    folder = tmp_path / "MyGame"
    project_id = add_project(conn, folder)
    write(folder, "keep.md", "one")
    write(folder, "gone.md")
    scan_project(conn, project_id, folder)
    conn.execute("UPDATE assets SET tags = 'important' WHERE path = 'keep.md'")

    write(folder, "keep.md", "one two")
    write(folder, "new.md")
    (folder / "gone.md").unlink()
    assert scan_project(conn, project_id, folder) == 2

    assert paths(conn, project_id) == ["keep.md", "new.md"]
    keep = list_assets(conn, project_id)[0]
    assert keep["size"] == 7
    assert keep["tags"] == "important"  # a rescan never overwrites tags


def test_scan_only_touches_its_own_project(conn, tmp_path):
    first = add_project(conn, tmp_path / "A")
    second = add_project(conn, tmp_path / "B")
    write(tmp_path / "A", "a.md")
    write(tmp_path / "B", "b.md")
    scan_project(conn, first, tmp_path / "A")
    scan_project(conn, second, tmp_path / "B")

    (tmp_path / "A" / "a.md").unlink()
    scan_project(conn, first, tmp_path / "A")
    assert paths(conn, first) == []
    assert paths(conn, second) == ["b.md"]
