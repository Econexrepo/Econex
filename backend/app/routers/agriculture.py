"""
Dashboard router – economic indicators and chart data
Reads real data from the DATA WAREHOUSE (Supabase project 2)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from pathlib import Path
from app.routers.auth import get_current_user
from app.models.schemas import UserOut
from app.db import get_warehouse_db
import math

RESULTS_DIR = Path("results")

router = APIRouter()

@router.get("/charts/fao-multiline-trend")
async def get_fao_multiline_trend(
    top_n: int = Query(5, ge=1, le=20),
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):
    try:
        rows = db.execute(
            text("""
                WITH latest_year AS (
                    SELECT MAX(year) AS max_year
                    FROM gold.fact_fao_sl
                    WHERE value IS NOT NULL
                      AND domain_id = 5
                      AND element_id = 65
                ),
                top_items AS (
                    SELECT item_id
                    FROM gold.fact_fao_sl
                    WHERE value IS NOT NULL
                      AND domain_id = 5
                      AND element_id = 65
                      AND year = (SELECT max_year FROM latest_year)
                    ORDER BY value DESC
                    LIMIT :top_n
                )
                SELECT
                    f.year,
                    i.item_name AS category,
                    f.value
                FROM gold.fact_fao_sl f
                JOIN gold.dim_fao_item i
                    ON f.item_id = i.item_id
                WHERE f.value IS NOT NULL
                  AND f.domain_id = 5
                  AND f.element_id = 65
                  AND f.item_id IN (SELECT item_id FROM top_items)
                ORDER BY f.year, f.item_id
            """),
            {"top_n": top_n}
        ).fetchall()

        data = []

        for r in rows:
            try:
                year = int(r[0]) if r[0] is not None else None
                category = str(r[1]).strip() if r[1] is not None else None
                value = float(r[2]) if r[2] is not None else None

                if year is None or category is None or value is None:
                    continue

                if not math.isfinite(value):
                    continue

                data.append({
                    "year": year,
                    "category": category,
                    "value": value,
                })
            except (TypeError, ValueError):
                continue

        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/charts/fao-heatmap")
async def get_fao_heatmap(
    top_n: int = Query(5, ge=3, le=30),
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):
    try:
        rows = db.execute(
            text("""
                WITH latest_year AS (
                    SELECT MAX(year) AS max_year
                    FROM gold.fact_fao_sl
                    WHERE value IS NOT NULL
                      AND domain_id = 5
                      AND element_id = 65
                ),
                top_items AS (
                    SELECT item_id
                    FROM gold.fact_fao_sl
                    WHERE value IS NOT NULL
                      AND domain_id = 5
                      AND element_id = 65
                      AND year = (SELECT max_year FROM latest_year)
                    ORDER BY value DESC
                    LIMIT :top_n
                )
                SELECT
                    f.year,
                    i.item_name AS item,
                    f.value
                FROM gold.fact_fao_sl f
                JOIN gold.dim_fao_item i
                    ON f.item_id = i.item_id
                WHERE f.value IS NOT NULL
                  AND f.domain_id = 5
                  AND f.element_id = 65
                  AND f.item_id IN (SELECT item_id FROM top_items)
                ORDER BY i.item_name, f.year
            """),
            {"top_n": top_n}
        ).fetchall()

        data = []

        for r in rows:
            try:
                year = int(r[0]) if r[0] is not None else None
                item = str(r[1]).strip() if r[1] is not None else None
                value = float(r[2]) if r[2] is not None else None

                if year is None or item is None or value is None:
                    continue

                if not math.isfinite(value):
                    continue

                data.append({
                    "year": year,
                    "item": item,
                    "value": value,
                })
            except (TypeError, ValueError):
                continue

        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/charts/fao-latest-top-items")
async def get_fao_latest_top_items(
    top_n: int = Query(5, ge=1, le=20),
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):
    try:
        rows = db.execute(
            text("""
                WITH latest_year AS (
                    SELECT MAX(year) AS max_year
                    FROM gold.fact_fao_sl
                    WHERE value IS NOT NULL
                      AND domain_id = 5
                      AND element_id = 65
                )
                SELECT
                    i.item_name AS label,
                    f.value
                FROM gold.fact_fao_sl f
                JOIN gold.dim_fao_item i
                    ON f.item_id = i.item_id
                WHERE f.value IS NOT NULL
                  AND f.domain_id = 5
                  AND f.element_id = 65
                  AND f.year = (SELECT max_year FROM latest_year)
                ORDER BY f.value DESC
                LIMIT :top_n
            """),
            {"top_n": top_n}
        ).fetchall()

        data = []
        for r in rows:
            try:
                label = str(r[0]).strip() if r[0] is not None else None
                value = float(r[1]) if r[1] is not None else None

                if label is None or value is None:
                    continue

                data.append({
                    "label": label,
                    "value": value,
                })
            except (TypeError, ValueError):
                continue

        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/agri-effect-only")
async def get_agri_effect_only(
    horizon: str = Query("long_run"),
    top_n: int = Query(15, ge=5, le=50),
    _: UserOut = Depends(get_current_user),
):
    path = RESULTS_DIR / "Agriproduction_relationship_table.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Missing file: {path.resolve()}"
        )

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    df["group_label"] = df["group_label"].astype(str).str.strip()
    df["horizon"] = df["horizon"].astype(str).str.strip().str.lower()
    df["effect_value"] = pd.to_numeric(df["effect_value"], errors="coerce")

    df = df[df["horizon"] == horizon.lower()]
    df = df.dropna(subset=["group_label", "effect_value"])

    df["abs_effect"] = df["effect_value"].abs()
    df = df.sort_values("abs_effect", ascending=False).head(top_n)

    return {
        "data": [
            {
                "label": str(row["group_label"]),
                "value": float(row["effect_value"]),
            }
            for _, row in df.iterrows()
        ]
    }


@router.get("/charts/ardl-short-significance")
async def get_ardl_short_significance(_: UserOut = Depends(get_current_user)):

    
    short_path = RESULTS_DIR / "rsui_unemployment_by_age_short_run_results.csv"

   
    short_df = pd.read_csv(short_path)

    
    short_df = short_df.rename(columns={
        "age_group_label": "label",    
        "age_unemp_coef": "value",      
        "age_unemp_pvalue": "p_value",  
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
        "data": short_df[["label", "value", "p_value", "is_significant"]].to_dict(orient="records")
    }


# ─────────────────────────────────────────────────────────
# Insights
# ─────────────────────────────────────────────────────────
@router.get("/insights")
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