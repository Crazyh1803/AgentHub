"""FastAPI routes."""

from contextlib import asynccontextmanager, closing

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import connect, init_db
from app.projects import ProjectError, create_project, list_projects, load_types
from app.settings import ROOT, ensure_folders, load_settings

WEB_DIR = ROOT / "web"
THEMES_DIR = ROOT / "themes"
TYPES_DIR = ROOT / "types"

settings = load_settings()
templates = Jinja2Templates(directory=WEB_DIR / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_folders(settings)
    with closing(connect(settings.db_path)) as conn:
        init_db(conn)
    yield


app = FastAPI(title="Agent Hub", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/themes", StaticFiles(directory=THEMES_DIR), name="themes")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    with closing(connect(settings.db_path)) as conn:
        context = _projects_context(conn)
    context["theme"] = settings.default_theme
    return templates.TemplateResponse(request, "index.html", context)


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
            create_project(conn, settings.projects_root, types[type], name, goal)
            form = {}
        except ProjectError as exc:
            error = str(exc)
        context = _projects_context(conn, form=form, error=error)
    return templates.TemplateResponse(request, "_projects.html", context)


def _projects_context(conn, form: dict | None = None, error: str | None = None) -> dict:
    return {
        "projects": list_projects(conn),
        "types": load_types(TYPES_DIR).values(),
        "form": form or {},
        "error": error,
    }
