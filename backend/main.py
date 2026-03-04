"""
Econex Backend – FastAPI Entry Point
"""

import pathlib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, dashboard, chat, settings

# ── CSV paths ──────────────────────────────────────────────────────────────────
_BASE_DIR = pathlib.Path(__file__).resolve().parent.parent   # Econex repo root
_ARDL_DIR = _BASE_DIR / "finalresults"

try:
    short_run_df = pd.read_csv(_ARDL_DIR / "gdp_shortRun.csv")
    long_run_df  = pd.read_csv(_ARDL_DIR / "gdp_longRun.csv")
    print(f"[main] ARDL CSVs loaded from: {_ARDL_DIR}")
except FileNotFoundError as e:
    raise RuntimeError(
        f"CSV file not found: {e}. "
        f"Expected files inside: {_ARDL_DIR}"
    ) from e

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Econex API",
    description="Backend API for the Econex Economic Intelligence Platform",
    version="1.0.0",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (uploaded avatars) ───────────────────────────────────────────
_UPLOADS_DIR = pathlib.Path(__file__).resolve().parent / "uploads"
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
("_UPLOADS_DIR" and (_UPLOADS_DIR / "avatars").mkdir(parents=True, exist_ok=True))
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/auth",      tags=["Auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(chat.router,      prefix="/api/chat",      tags=["Chat"])
app.include_router(settings.router,  prefix="/api/settings",  tags=["Settings"])


# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "Econex API",
        "ardl_data": {
            "short_run_rows": len(short_run_df),
            "long_run_rows":  len(long_run_df),
        }
    }


# ── GDP / ARDL direct-data endpoints ──────────────────────────────────────────

class GDPAnalyzeRequest(BaseModel):
    message: str


def _compute_impact_shares() -> dict:
    """Compute sector impact shares from long-run effects."""
    total = long_run_df["long_run_effect"].abs().sum()
    shares = {}
    for _, row in long_run_df.iterrows():
        shares[row["sector_name"]] = round(
            abs(float(row["long_run_effect"])) / total * 100, 1
        )
    return shares


@app.get("/api/gdp/sectors", tags=["GDP Analysis"])
def get_all_sectors():
    """Return all sector data from ARDL CSVs with computed impact shares."""
    shares = _compute_impact_shares()
    result = []
    for _, row in long_run_df.iterrows():
        sector = row["sector_name"]
        sr_row = short_run_df[short_run_df["sector_name"] == sector]

        result.append({
            "sector":           sector,
            "n_obs":            int(row["n_obs"]),
            "long_run_effect":  float(row["long_run_effect"]),
            "impact_share_pct": shares.get(sector, 0),
            "long_run_aic":     float(row["aic"]),
            "long_run_bic":     float(row["bic"]),
            "short_run_coef":   float(sr_row.iloc[0]["gdp_coef"])   if not sr_row.empty else None,
            "short_run_pvalue": float(sr_row.iloc[0]["gdp_pvalue"]) if not sr_row.empty else None,
            "short_run_sig":    (float(sr_row.iloc[0]["gdp_pvalue"]) < 0.05) if not sr_row.empty else False,
        })
    return result


@app.post("/api/gdp/analyze", tags=["GDP Analysis"])
def gdp_analyze(request: GDPAnalyzeRequest):
    """
    Keyword-based sector lookup from ARDL CSVs.
    No LLM required — returns JSON data for the matched sector.
    """
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
            "sector":           sector,
            "long_run_effect":  float(lr.iloc[0]["long_run_effect"]),
            "impact_share_pct": shares.get(sector, 0),
            "short_run_coef":   float(sr.iloc[0]["gdp_coef"])   if not sr.empty else None,
            "short_run_pvalue": float(sr.iloc[0]["gdp_pvalue"]) if not sr.empty else None,
            "short_run_sig":    (float(sr.iloc[0]["gdp_pvalue"]) < 0.05) if not sr.empty else False,
        }

    # No sector matched — return all
    return {"all_sectors": get_all_sectors()}