"""
Dashboard router – economic indicators and chart data
Reads real data from the DATA WAREHOUSE (Supabase project 2)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.routers.auth import get_current_user
from app.models.schemas import UserOut
from app.db import get_warehouse_db

router = APIRouter()


# ─────────────────────────────────────────────────────────
# Dashboard Stats
# ─────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    row = db.execute(text("""
        SELECT
            AVG(rsui_annual_weighted) AS rsui_avg
        FROM gold.fact_rsui_annual
    """)).fetchone()

    return {
        "rsui_average": float(row[0]) if row and row[0] else 0
    }


# ─────────────────────────────────────────────────────────
# RSUI Trend (line chart)
# ─────────────────────────────────────────────────────────
@router.get("/rsui-trend")
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

    elif range == "10y":
        data = data[-10:]

    return {"range": range, "data": data}


# ─────────────────────────────────────────────────────────
# PCE Breakdown
# ─────────────────────────────────────────────────────────
@router.get("/charts/pce")
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
        "chart": "pce",
        "data": [
            {
                "label": r[0],
                "value": float(r[1])
            }
            for r in rows
        ]
    }

# ─────────────────────────────────────────────────────────
# GDP Sector Chart
# ─────────────────────────────────────────────────────────
@router.get("/charts/gdp-sector")
async def get_gdp_sector_chart(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):

    rows = db.execute(text("""
        SELECT
            sector_label,
            SUM(gdp_value)
        FROM gold.fact_gdp_sector
        GROUP BY sector_label
    """)).fetchall()

    return {
        "chart": "gdp_sector",
        "data": [
            {"label": r[0], "value": float(r[1])}
            for r in rows
        ]
    }


# ─────────────────────────────────────────────────────────
# Insights (can later come from ML / analysis engine)
# ─────────────────────────────────────────────────────────
@router.get("/insights")
async def get_insights(_: UserOut = Depends(get_current_user)):

    insights = [
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
        },
    ]

    return {"insights": insights}