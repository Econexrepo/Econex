"""
Dashboard router – economic indicators and chart data
Reads real data from the DATA WAREHOUSE (Supabase project 2)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from pathlib import Path
from app.routers.auth import get_current_user
from app.models.schemas import UserOut
from app.db import get_warehouse_db
from app.cache import cached_endpoint

RESULTS_DIR = Path("results")

router = APIRouter()


# ─────────────────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────────────────
@router.get("/stats")
@cached_endpoint
async def get_stats(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    # RSUI average
    rsui_row = db.execute(text("""
        SELECT AVG(rsui_annual_weighted)
        FROM gold.fact_rsui_annual
    """)).fetchone()

    # Latest PCE growth rate
    pce_row = db.execute(text("""
                SELECT
            AVG(f.pce_growth_rate) AS change
        FROM gold.fact_pce f
        JOIN gold.dim_year y
        ON y.year_id = f.year_id
        WHERE y.year = (
            SELECT MAX(year)
            FROM gold.dim_year
        )
    """)).fetchone()

    return {
        "rsui_average": float(rsui_row[0]) if rsui_row and rsui_row[0] else 0,
        "personal_consumption_change": float(pce_row[0]) if pce_row and pce_row[0] else 0
    }


# ─────────────────────────────────────────────────────────
# RSUI Trend (Line Chart)
# ─────────────────────────────────────────────────────────
@router.get("/rsui-trend")
@cached_endpoint
async def get_rsui_trend(
    range: str = "all",
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            y.year,
            f.rsui_annual_weighted
        FROM gold.fact_rsui_annual f
        JOIN gold.dim_year y
        ON y.year_id = f.year_id
        ORDER BY y.year
    """)).fetchall()

    data = [
        {"year": r[0], "value": float(r[1])}
        for r in rows
    ]

    if range == "5y":
        data = data[-5:]

    if range == "10y":
        data = data[-10:]

    return {"data": data}


# ─────────────────────────────────────────────────────────
# PCE Chart
# ─────────────────────────────────────────────────────────
@router.get("/charts/pce")
@cached_endpoint
async def get_pce_chart(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            category_label,
            SUM(pce_actual_value) AS value
        FROM gold.fact_pce
        GROUP BY category_label
        ORDER BY category_label
    """)).fetchall()

    return {
        "data": [
            {"label": r[0], "value": float(r[1])}
            for r in rows
        ]
    }

# ─────────────────────────────────────────────────────────
# PCE Growth Value Trend
# ─────────────────────────────────────────────────────────
@router.get("/charts/pce-growth-value")
@cached_endpoint
async def get_pce_growth_value(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            y.year,
            SUM(f.pce_growth_value) AS value
        FROM gold.fact_pce f
        JOIN gold.dim_year y
          ON y.year_id = f.year_id
        GROUP BY y.year
        ORDER BY y.year
    """)).fetchall()

    return {
        "data": [
            {"year": r[0], "value": float(r[1])}
            for r in rows
        ]
    }


# ─────────────────────────────────────────────────────────
# PCE Growth Rate Trend
# ─────────────────────────────────────────────────────────
@router.get("/charts/pce-growth-rate")
@cached_endpoint
async def get_pce_growth_rate(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            y.year,
            AVG(f.pce_growth_rate) AS rate
        FROM gold.fact_pce f
        JOIN gold.dim_year y
          ON y.year_id = f.year_id
        GROUP BY y.year
        ORDER BY y.year
    """)).fetchall()

    return {
        "data": [
            {"year": r[0], "value": float(r[1])}
            for r in rows
        ]
    }

# ─────────────────────────────────────────────────────────
# PCE Category Share (Donut)
# ─────────────────────────────────────────────────────────
@router.get("/charts/pce-share")
@cached_endpoint
async def get_pce_share(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            category_raw,
            AVG(pce_percentage) AS value
        FROM gold.fact_pce
        GROUP BY category_raw
        ORDER BY value DESC
    """)).fetchall()

    return {
        "data": [
            {"label": r[0], "value": float(r[1])}
            for r in rows
        ]
    }

# ─────────────────────────────────────────────────────────
# PCE Volatility (Std Dev of Growth Rate)
# ─────────────────────────────────────────────────────────
@router.get("/charts/pce-volatility")
@cached_endpoint
async def get_pce_volatility(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            category_raw AS label,
            STDDEV(pce_growth_rate) AS value
        FROM gold.fact_pce
        WHERE pce_growth_rate IS NOT NULL
        GROUP BY category_raw
        HAVING COUNT(*) > 1
        ORDER BY value DESC
    """)).fetchall()

    return {
        "data": [
            {"label": r[0], "value": float(r[1])}
            for r in rows
        ]
    }

# ─────────────────────────────────────────────────────────
# ARDL Model Impact (Short + Long Run)
# ─────────────────────────────────────────────────────────
@router.get("/charts/ardl-impact")
@cached_endpoint
async def get_ardl_impact(_: UserOut = Depends(get_current_user)):

    short_path = RESULTS_DIR / "short_run_pce.csv"
    long_path = RESULTS_DIR / "long_run_pce.csv"

    short_df = pd.read_csv(short_path)
    long_df = pd.read_csv(long_path)

    # Rename columns to match frontend expectation
    short_df = short_df.rename(columns={
        "category_label": "variable",
        "coef": "short_run"
    })

    long_df = long_df.rename(columns={
        "category_label": "variable",
        "long_run_effect": "long_run"
    })

    # Keep only required columns
    short_df = short_df[["variable", "short_run"]]
    long_df = long_df[["variable", "long_run"]]

    merged = short_df.merge(long_df, on="variable")

    return {
        "data": merged.to_dict(orient="records")
    }

    # ─────────────────────────────────────────────────────────
# ARDL Short-run Coefficient + Significance
# ─────────────────────────────────────────────────────────
@router.get("/charts/ardl-short-significance")
@cached_endpoint
async def get_ardl_short_significance(_: UserOut = Depends(get_current_user)):

    short_path = RESULTS_DIR / "short_run_pce.csv"

    short_df = pd.read_csv(short_path)

    
    short_df = short_df.rename(columns={
        "category_label": "label",
        "coef": "value",
        "pvalue": "p_value",
    })

    
    cols_needed = ["label", "value", "p_value"]
    missing = [c for c in cols_needed if c not in short_df.columns]
    if missing:
        return {"error": f"Missing columns in short_run_pce.csv: {missing}"}

    short_df = short_df[cols_needed].copy()

    
    short_df["value"] = pd.to_numeric(short_df["value"], errors="coerce")
    short_df["p_value"] = pd.to_numeric(short_df["p_value"], errors="coerce")

    short_df = short_df.dropna(subset=["label", "value", "p_value"])


    short_df["is_significant"] = short_df["p_value"] < 0.05

    short_df["abs_value"] = short_df["value"].abs()
    short_df = short_df.sort_values("abs_value", ascending=False)

    return {
        "data": short_df[["label", "value", "p_value", "is_significant"]]
        .to_dict(orient="records")
    }


# ─────────────────────────────────────────────────────────
# Insights
# ─────────────────────────────────────────────────────────
@router.get("/insights")
@cached_endpoint
async def get_insights(_: UserOut = Depends(get_current_user)):

    return {
        "insights": [
            {
                "id": "ins-1",
                "type": "danger",
                "icon": "⚠️",
                "title": "High Risk Alert",
                "description": "RSUI indicates increasing socio-economic pressure."
            },
            {
                "id": "ins-2",
                "type": "warning",
                "icon": "📈",
                "title": "Consumption Volatility",
                "description": "Personal consumption categories fluctuating significantly."
            },
            {
                "id": "ins-3",
                "type": "success",
                "icon": "🌾",
                "title": "Agriculture Sector Stable",
                "description": "Agricultural output stable relative to RSUI baseline."
            }
        ]
    }