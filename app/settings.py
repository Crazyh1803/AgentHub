"""Loads config/settings.yaml and creates the folders it names."""

from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "config" / "settings.yaml"


@dataclass(frozen=True)
class Settings:
    projects_root: Path
    db_path: Path
    default_theme: str


def load_settings(path: Path = SETTINGS_FILE, root: Path = ROOT) -> Settings:
    """Read the settings file. `~` is expanded; relative paths are under `root`."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Settings(
        projects_root=_resolve(raw["projects_root"], root),
        db_path=_resolve(raw["db_path"], root),
        default_theme=raw["default_theme"],
    )


def ensure_folders(settings: Settings) -> None:
    """Create the projects folder and the database's folder if missing."""
    settings.projects_root.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)


def _resolve(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path
