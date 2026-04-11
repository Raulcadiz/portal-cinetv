"""
IPTVSur Portal — FastAPI application entry point.

Start the server:
    uvicorn src.main:app --reload --port 8000
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import admin, epg, portal, sync, device_auth, device_lists, admin_users, contenido
from src.core.config import settings
from src.core.database import create_tables


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    # Ensure the data directory exists (for SQLite file)
    os.makedirs("data", exist_ok=True)
    # Create DB tables (idempotent — skips existing tables)
    await create_tables()
    yield
    # Shutdown: nothing to clean up for SQLite


# ── App instance ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Cine Tv Portal",
    description=(
        "Portal web para gestionar listas IPTV y licencias de Cine Tv. "
        "La app Android consulta /api/device/* para registrarse y gestionar sus listas."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(admin.router,        prefix="/api/admin",         tags=["admin"])
app.include_router(admin_users.router,  prefix="/api/admin",         tags=["admin — usuarios"])
app.include_router(sync.router,         prefix="/api",               tags=["sync"])
app.include_router(portal.router,       prefix="/api/portal",        tags=["portal — listas"])
app.include_router(epg.router,          prefix="/api/portal/epg",    tags=["portal — EPG"])
app.include_router(device_auth.router,  prefix="/api/device",        tags=["device — licencia"])
app.include_router(device_lists.router, prefix="/api/device/lists",  tags=["device — listas"])
app.include_router(contenido.router,       prefix="/api/portal",        tags=["portal — contenido"])

# ── Static files (portal web) ─────────────────────────────────────────────────
# Serve the web portal HTML/CSS/JS from src/web/
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.isdir(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="web")


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"], summary="Health check")
async def health() -> dict:
    """Returns 200 OK if the service is running. Used by Docker HEALTHCHECK and CI."""
    return {"status": "ok", "service": "cinetv-portal"}
