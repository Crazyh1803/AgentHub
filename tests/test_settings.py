from pathlib import Path

from app.settings import ensure_folders, load_settings


def write_settings(tmp_path: Path, projects_root: str) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(
        f"projects_root: {projects_root}\n"
        "db_path: data/hub.db\n"
        "default_theme: comfy\n",
        encoding="utf-8",
    )
    return path


def test_relative_paths_are_under_root(tmp_path):
    settings = load_settings(write_settings(tmp_path, "projects"), root=tmp_path)
    assert settings.projects_root == tmp_path / "projects"
    assert settings.db_path == tmp_path / "data" / "hub.db"
    assert settings.default_theme == "comfy"


def test_tilde_is_expanded(tmp_path):
    settings = load_settings(write_settings(tmp_path, "~/Hub"), root=tmp_path)
    assert settings.projects_root == Path.home() / "Hub"


def test_ensure_folders_creates_missing_folders(tmp_path):
    settings = load_settings(write_settings(tmp_path, "projects"), root=tmp_path)
    ensure_folders(settings)
    assert settings.projects_root.is_dir()
    assert settings.db_path.parent.is_dir()
    assert not settings.db_path.exists()
