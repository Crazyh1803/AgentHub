from contextlib import closing

import pytest
from fastapi.testclient import TestClient

from app import main
from app.db import connect, init_db
from app.settings import Settings


@pytest.fixture
def git_identity(monkeypatch):
    """Let git commit in tests even where no global user is configured."""
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Hub Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "hub-test@example.invalid")


@pytest.fixture
def settings(tmp_path):
    return Settings(
        projects_root=tmp_path / "projects",
        db_path=tmp_path / "hub.db",
        default_theme="comfy",
    )


@pytest.fixture
def client(settings, git_identity, monkeypatch):
    """The app, pointed at a temporary database and projects folder."""
    settings.projects_root.mkdir()
    with closing(connect(settings.db_path)) as conn:
        init_db(conn)
    monkeypatch.setattr(main, "settings", settings)
    return TestClient(main.app)
