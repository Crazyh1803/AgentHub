import sqlite3

import pytest

from app.db import TASK_TYPES, connect, init_db

NOW = "2026-11-16T12:00:00+00:00"


@pytest.fixture
def conn(tmp_path):
    conn = connect(tmp_path / "hub.db")
    init_db(conn)
    yield conn
    conn.close()


def add_project(conn, name="MyGame"):
    cur = conn.execute(
        "INSERT INTO projects (name, type, path, created_at) VALUES (?, ?, ?, ?)",
        (name, "game", f"/projects/{name}", NOW),
    )
    return cur.lastrowid


def add_task(conn, project_id, type="code"):
    cur = conn.execute(
        "INSERT INTO tasks (project_id, title, type, created_at) VALUES (?, ?, ?, ?)",
        (project_id, "Add a menu", type, NOW),
    )
    return cur.lastrowid


def test_init_creates_the_four_tables(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    assert {row["name"] for row in rows} == {"projects", "tasks", "runs", "assets"}


def test_init_is_safe_to_run_twice(conn):
    add_project(conn)
    init_db(conn)
    assert conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1


def test_defaults(conn):
    task_id = add_task(conn, add_project(conn))
    project = conn.execute("SELECT * FROM projects").fetchone()
    task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    assert project["status"] == "active"
    assert (task["agent"], task["status"]) == ("auto", "pending")


def test_project_names_are_unique(conn):
    add_project(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_project(conn)


def test_every_v01_task_type_is_accepted(conn):
    project_id = add_project(conn)
    for task_type in TASK_TYPES:
        add_task(conn, project_id, task_type)


def test_unknown_task_type_is_rejected(conn):
    project_id = add_project(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_task(conn, project_id, "images")


def test_task_needs_an_existing_project(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_task(conn, project_id=999)


def test_run_can_start_unfinished_and_be_completed(conn):
    task_id = add_task(conn, add_project(conn))
    run_id = conn.execute(
        "INSERT INTO runs (task_id, agent, started_at) VALUES (?, ?, ?)",
        (task_id, "claude_code", NOW),
    ).lastrowid
    conn.execute("UPDATE runs SET exit_code = 0, duration_s = 1.5 WHERE id = ?", (run_id,))
    run = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    assert (run["exit_code"], run["duration_s"], run["finished_at"]) == (0, 1.5, None)


def test_asset_path_is_unique_per_project(conn):
    first, second = add_project(conn, "A"), add_project(conn, "B")
    insert = "INSERT INTO assets (project_id, path, type, size) VALUES (?, ?, ?, ?)"
    conn.execute(insert, (first, "assets/logo.png", "image", 1024))
    conn.execute(insert, (second, "assets/logo.png", "image", 1024))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(insert, (first, "assets/logo.png", "image", 2048))


def test_deleting_a_project_removes_its_rows(conn):
    project_id = add_project(conn)
    add_task(conn, project_id)
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0
