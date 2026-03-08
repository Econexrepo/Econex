"""
Econex Backend – FastAPI Entry Point
"""

import logging
import pathlib

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.routers import auth, dashboard, chat, settings, unemployment, wages, gdp, governmentexpenditure, agriculture
from dotenv import load_dotenv


load_dotenv()  # loads .env into os.environ

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("econex.main")

# ── Paths ──────────────────────────────────────────────────────────────────────
_BACKEND_DIR = pathlib.Path(__file__).resolve().parent          # .../backend
_REPO_ROOT = _BACKEND_DIR.parent                                # .../Econex

# Try repo-root ardloutputs first (your current design), then backend/ardloutputs as fallback
# _ARDL_CANDIDATES = [
#     _REPO_ROOT / "ardloutputs",
#     _BACKEND_DIR / "ardloutputs",
# ]

# _ARDL_DIR = next((p for p in _ARDL_CANDIDATES if p.exists()), _ARDL_CANDIDATES[0])
# _SHORT_RUN_PATH = _ARDL_DIR / "gdp_shortRun.csv"
# _LONG_RUN_PATH = _ARDL_DIR / "gdp_longRun.csv"


def _read_csv_or_empty(path: pathlib.Path, label: str) -> pd.DataFrame:
    """Load CSV if present; otherwise return empty DataFrame (do NOT crash app startup)."""
    if not path.exists():
        logger.warning("[main] Missing %s at: %s", label, path)
        return pd.DataFrame()

    try:
        df = pd.read_csv(path)
        logger.info("[main] Loaded %s from %s — %d rows", label, path, len(df))
        return df
    except Exception as e:
        logger.exception("[main] Failed to load %s from %s: %s", label, path, e)
        return pd.DataFrame()


# # Load ARDL data safely at startup/import time
# short_run_df = _read_csv_or_empty(_SHORT_RUN_PATH, "gdp_shortRun.csv")
# long_run_df = _read_csv_or_empty(_LONG_RUN_PATH, "gdp_longRun.csv")


def _available_csvs_in_ardl_dir() -> list[str]:
    if not _ARDL_DIR.exists():
        return []
    return sorted([p.name for p in _ARDL_DIR.glob("*.csv")])


def _ensure_ardl_ready() -> None:
    """
    Ensure ARDL CSVs exist and contain the required columns before GDP endpoints run.
    Raises HTTP 503 (service unavailable) instead of crashing the whole app.
    """
    if short_run_df.empty or long_run_df.empty:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "ARDL CSV data is not available yet.",
                "expected_dir": str(_ARDL_DIR),
                "expected_files": ["gdp_shortRun.csv", "gdp_longRun.csv"],
                "available_csvs": _available_csvs_in_ardl_dir(),
                "short_run_loaded": not short_run_df.empty,
                "long_run_loaded": not long_run_df.empty,
            },
        )

    required_long = {"sector_name", "long_run_effect", "n_obs", "aic", "bic"}
    required_short = {"sector_name", "gdp_coef", "gdp_pvalue"}

    missing_long = sorted(required_long - set(long_run_df.columns))
    missing_short = sorted(required_short - set(short_run_df.columns))

    if missing_long or missing_short:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "ARDL CSV schema mismatch.",
                "missing_long_run_columns": missing_long,
                "missing_short_run_columns": missing_short,
                "long_run_columns": list(long_run_df.columns),
                "short_run_columns": list(short_run_df.columns),
            },
        )


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


# ── Health ─────────────────────────────────────────────────────────────────────
# @app.get("/api/health", tags=["Health"])
# async def health_check():
#     return {
#         "status": "ok",
#         "service": "Econex API",
#         "ardl_data": {
#             "resolved_ardl_dir": str(_ARDL_DIR),
#             "expected_files": {
#                 "short_run": str(_SHORT_RUN_PATH),
#                 "long_run": str(_LONG_RUN_PATH),
#             },
#             "available_csvs": _available_csvs_in_ardl_dir(),
#             "short_run_loaded": not short_run_df.empty,
#             "long_run_loaded": not long_run_df.empty,
#             "short_run_rows": int(len(short_run_df)) if not short_run_df.empty else 0,
#             "long_run_rows": int(len(long_run_df)) if not long_run_df.empty else 0,
#         },
#     }


# ── GDP / ARDL direct-data endpoints ──────────────────────────────────────────
class GDPAnalyzeRequest(BaseModel):
    message: str


def _compute_impact_shares() -> dict[str, float]:
    """Compute sector impact shares from long-run effects."""
    _ensure_ardl_ready()

    total = long_run_df["long_run_effect"].abs().sum()
    if total == 0:
        return {str(row["sector_name"]): 0.0 for _, row in long_run_df.iterrows()}

    shares: dict[str, float] = {}
    for _, row in long_run_df.iterrows():
        sector_name = str(row["sector_name"])
        shares[sector_name] = round(abs(float(row["long_run_effect"])) / float(total) * 100, 1)
    return shares


@app.get("/api/gdp/sectors", tags=["GDP Analysis"])
def get_all_sectors():
    """Return all sector data from ARDL CSVs with computed impact shares."""
    _ensure_ardl_ready()

    shares = _compute_impact_shares()
    result = []

    for _, row in long_run_df.iterrows():
        sector = str(row["sector_name"])
        sr_row = short_run_df[short_run_df["sector_name"] == sector]

        result.append(
            {
                "sector": sector,
                "n_obs": int(row["n_obs"]),
                "long_run_effect": float(row["long_run_effect"]),
                "impact_share_pct": shares.get(sector, 0.0),
                "long_run_aic": float(row["aic"]),
                "long_run_bic": float(row["bic"]),
                "short_run_coef": float(sr_row.iloc[0]["gdp_coef"]) if not sr_row.empty else None,
                "short_run_pvalue": float(sr_row.iloc[0]["gdp_pvalue"]) if not sr_row.empty else None,
                "short_run_sig": (float(sr_row.iloc[0]["gdp_pvalue"]) < 0.05) if not sr_row.empty else False,
            }
        )

    return result


@app.post("/api/gdp/analyze", tags=["GDP Analysis"])
def gdp_analyze(request: GDPAnalyzeRequest):
    """
    Keyword-based sector lookup from ARDL CSVs.
    No LLM required — returns JSON data for the matched sector.
    """
    _ensure_ardl_ready()

    q = request.message.lower()
    shares = _compute_impact_shares()

    sector = None
    if "agriculture" in q or "agr" in q or "farm" in q:
        sector = "Agriculture"
    elif "industry" in q or "ind" in q or "manufactur" in q:
        sector = "Industry"
    elif "service" in q or "srv" in q:
        sector = "Services"

    if sector:
        lr = long_run_df[long_run_df["sector_name"] == sector]
        sr = short_run_df[short_run_df["sector_name"] == sector]

        if lr.empty:
            raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found.")

        return {
            "sector": sector,
            "long_run_effect": float(lr.iloc[0]["long_run_effect"]),
            "impact_share_pct": shares.get(sector, 0.0),
            "short_run_coef": float(sr.iloc[0]["gdp_coef"]) if not sr.empty else None,
            "short_run_pvalue": float(sr.iloc[0]["gdp_pvalue"]) if not sr.empty else None,
            "short_run_sig": (float(sr.iloc[0]["gdp_pvalue"]) < 0.05) if not sr.empty else False,
        }

    # No sector matched — return all sectors
    return {"all_sectors": get_all_sectors()}