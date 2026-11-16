"""FastAPI routes."""

from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.adapters import check_health, load_adapters
from app.assets import list_assets, scan_project
from app.db import connect, init_db
from app.projects import (
    ProjectError,
    create_project,
    get_project,
    list_projects,
    load_types,
)
from app.settings import ROOT, ensure_folders, load_settings

WEB_DIR = ROOT / "web"
THEMES_DIR = ROOT / "themes"
TYPES_DIR = ROOT / "types"

settings = load_settings()
templates = Jinja2Templates(directory=WEB_DIR / "templates")
adapters = load_adapters()
health: dict[str, bool] = {}    # adapter name -> available; filled at startup


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_folders(settings)
    with closing(connect(settings.db_path)) as conn:
        init_db(conn)
    health.update(check_health(adapters))
    yield


app = FastAPI(title="Agent Hub", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/themes", StaticFiles(directory=THEMES_DIR), name="themes")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    with closing(connect(settings.db_path)) as conn:
        context = _projects_context(conn)
    return _page(request, "index.html", context)


@app.post("/projects", response_class=HTMLResponse)
def new_project(
    request: Request,
    name: str = Form(""),
    type: str = Form(""),
    goal: str = Form(""),
) -> HTMLResponse:
    """Create a project, then return the projects section for htmx to swap in."""
    types = load_types(TYPES_DIR)
    form = {"name": name, "type": type, "goal": goal}
    error = None
    with closing(connect(settings.db_path)) as conn:
        try:
            if type not in types:
                raise ProjectError("Pick a project type.")
            folder = create_project(conn, settings.projects_root, types[type], name, goal)
            project_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            scan_project(conn, project_id, folder)
            form = {}
        except ProjectError as exc:
            error = str(exc)
        context = _projects_context(conn, form=form, error=error)
    return templates.TemplateResponse(request, "_projects.html", context)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
def project_page(request: Request, project_id: int) -> HTMLResponse:
    with closing(connect(settings.db_path)) as conn:
        project = _project_or_404(conn, project_id)
        context = {"project": project, "assets": list_assets(conn, project_id)}
    return _page(request, "project.html", context)


@app.post("/projects/{project_id}/rescan", response_class=HTMLResponse)
def rescan(request: Request, project_id: int) -> HTMLResponse:
    """Rescan the project folder, then return the assets section for htmx."""
    with closing(connect(settings.db_path)) as conn:
        project = _project_or_404(conn, project_id)
        folder = Path(project["path"])
        error = None
        if folder.is_dir():
            scan_project(conn, project_id, folder)
        else:
            error = f"The project folder is missing: {folder}"
        context = {
            "project": project,
            "assets": list_assets(conn, project_id),
            "error": error,
        }
    return templates.TemplateResponse(request, "_assets.html", context)


@app.post("/health/recheck", response_class=HTMLResponse)
def recheck_health(request: Request) -> HTMLResponse:
    """Run the adapter checks again, then return the header list for htmx."""
    health.update(check_health(adapters))
    return templates.TemplateResponse(request, "_health.html", {"health": health})


def _page(request: Request, template: str, context: dict) -> HTMLResponse:
    context["theme"] = settings.default_theme
    context["health"] = health
    return templates.TemplateResponse(request, template, context)


def _project_or_404(conn, project_id: int):
    project = get_project(conn, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _projects_context(conn, form: dict | None = None, error: str | None = None) -> dict:
    return {
        "projects": list_projects(conn),
        "types": load_types(TYPES_DIR).values(),
        "form": form or {},
        "error": error,
    }
