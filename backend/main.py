"""
Econex Backend – FastAPI Entry Point
"""

import logging
import pathlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, dashboard, chat, settings, unemployment, wages, gdp, governmentexpenditure, agriculture, graphs
from dotenv import load_dotenv


load_dotenv()  # loads .env into os.environ

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("econex.main")

# ── Paths ──────────────────────────────────────────────────────────────────────
_BACKEND_DIR = pathlib.Path(__file__).resolve().parent          # .../backend


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Econex API",
    description="Backend API for the Econex Economic Intelligence Platform",
    version="1.0.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded avatars) ───────────────────────────────────────────
_UPLOADS_DIR = _BACKEND_DIR / "uploads"
(_UPLOADS_DIR / "avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(unemployment.router, prefix="/api/unemployment", tags=["Unemployment"])
app.include_router(wages.router, prefix="/api/wages", tags=["wages"])
app.include_router(gdp.router, prefix="/api/gdp", tags=["gdp"])
app.include_router(agriculture.router, prefix="/api/agriculture", tags=["agriculture"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(governmentexpenditure.router, prefix="/api/government-expenditure", tags=["Government Expenditure"])
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(graphs.router, prefix="/api/graphs", tags=["Graphs"])
