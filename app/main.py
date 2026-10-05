"""FastAPI application entry point."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import APP_NAME, APP_VERSION, ALLOWED_ORIGINS

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title=APP_NAME, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ───────────────────────────────────────────────────────────
# 1. API routes FIRST — they must not be shadowed by anything
# ───────────────────────────────────────────────────────────
app.include_router(router)


# ───────────────────────────────────────────────────────────
# 2. HTML page routes SECOND
# ───────────────────────────────────────────────────────────
def _html_page(filename: str) -> FileResponse:
    """Serve an HTML file with explicit UTF-8 charset."""
    public_path = PUBLIC_DIR / filename
    static_path = STATIC_DIR / filename
    path = public_path if public_path.exists() else static_path
    return FileResponse(
        str(path),
        media_type="text/html; charset=utf-8",
    )

@app.get("/")
def index() -> FileResponse:
    return _html_page("index.html")


@app.get("/learn")
def learn() -> FileResponse:
    return _html_page("learn.html")


# ───────────────────────────────────────────────────────────
# 3. Static mounts LAST
# ───────────────────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if PUBLIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PUBLIC_DIR), html=True), name="public")