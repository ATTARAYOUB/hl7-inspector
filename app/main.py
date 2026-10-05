"""FastAPI application entry point."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import APP_NAME, APP_VERSION, ALLOWED_ORIGINS

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
STATIC_DIR = Path(__file__).resolve().parent / "static"

# ─────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────
app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# 1. API routes FIRST (so /api/* is never shadowed)
# ─────────────────────────────────────────────────────────────
app.include_router(router)

# ─────────────────────────────────────────────────────────────
# 2. HTML page routes SECOND
# ─────────────────────────────────────────────────────────────
def _html_page(filename: str) -> FileResponse:
    """Serve an HTML file, preferring public/ then app/static/."""
    public_path = PUBLIC_DIR / filename
    static_path = STATIC_DIR / filename
    if public_path.exists():
        return FileResponse(str(public_path))
    return FileResponse(str(static_path))


@app.get("/")
def index() -> FileResponse:
    return _html_page("index.html")


@app.get("/learn")
def learn() -> FileResponse:
    return _html_page("learn.html")


# ─────────────────────────────────────────────────────────────
# 3. Static mounts LAST (so they don't shadow API or HTML routes)
# ─────────────────────────────────────────────────────────────
# Mount /static → app/static (kept for backward compatibility)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount / → public/ (serves CSS/JS/HTML at root for Vercel)
if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")