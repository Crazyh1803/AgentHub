"""FastAPI routes. Step 1: serves a blank themed page, nothing else."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import connect, init_db
from app.settings import ROOT, ensure_folders, load_settings

WEB_DIR = ROOT / "web"
THEMES_DIR = ROOT / "themes"

settings = load_settings()
templates = Jinja2Templates(directory=WEB_DIR / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_folders(settings)
    conn = connect(settings.db_path)
    init_db(conn)
    conn.close()
    yield


app = FastAPI(title="Agent Hub", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
app.mount("/themes", StaticFiles(directory=THEMES_DIR), name="themes")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "index.html", {"theme": settings.default_theme}
    )
