"""Asset index: scans a project folder into the assets table."""

import sqlite3
from pathlib import Path

# File extension -> asset type. Anything not listed is "other".
TYPES_BY_EXTENSION = {
    "image": "png jpg jpeg gif webp svg bmp tga psd",
    "model": "blend fbx obj gltf glb stl scad 3mf",
    "audio": "wav mp3 ogg flac",
    "video": "mp4 mov webm",
    "code": "py js ts cs c cpp h gd lua rs go java html css sh ps1",
    "doc": "md txt pdf docx",
    "data": "json yaml yml toml csv xml ini gcode",
}
EXTENSION_TYPE = {
    ext: asset_type
    for asset_type, extensions in TYPES_BY_EXTENSION.items()
    for ext in extensions.split()
}


def asset_type(path: Path) -> str:
    return EXTENSION_TYPE.get(path.suffix.lower().lstrip("."), "other")


def find_files(folder: Path) -> list[Path]:
    """Every file under the folder, skipping hidden ones (.git, .gitkeep, ...)."""
    files = []
    for path in folder.rglob("*"):
        relative = path.relative_to(folder)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if path.is_file():
            files.append(relative)
    return sorted(files)


def scan_project(conn: sqlite3.Connection, project_id: int, folder: Path) -> int:
    """Bring the assets table in line with the folder. Returns the file count.

    New files are added, known files get their type and size refreshed (their
    tags are kept), and rows for files that are gone are removed.
    """
    files = find_files(folder)
    for relative in files:
        conn.execute(
            """
            INSERT INTO assets (project_id, path, type, size, tags)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT (project_id, path)
            DO UPDATE SET type = excluded.type, size = excluded.size
            """,
            (
                project_id,
                relative.as_posix(),
                asset_type(relative),
                (folder / relative).stat().st_size,
                ",".join(relative.parts[:-1]),  # default tags: the folder names
            ),
        )
    found = {relative.as_posix() for relative in files}
    known = conn.execute("SELECT path FROM assets WHERE project_id = ?", (project_id,))
    for (path,) in known.fetchall():
        if path not in found:
            conn.execute(
                "DELETE FROM assets WHERE project_id = ? AND path = ?", (project_id, path)
            )
    conn.commit()
    return len(files)


def list_assets(conn: sqlite3.Connection, project_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM assets WHERE project_id = ? ORDER BY path", (project_id,)
    ).fetchall()
