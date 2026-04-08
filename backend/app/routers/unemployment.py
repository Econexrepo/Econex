"""
Dashboard router – economic indicators and chart data
Reads real data from the DATA WAREHOUSE (Supabase project 2)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from pathlib import Path
from app.routers.auth import get_current_user
from app.models.schemas import UserOut
from app.db import get_warehouse_db

RESULTS_DIR = Path("results")

router = APIRouter()


# ─────────────────────────────────────────────────────────
# Unemployment by Age Group Trend (Multi-line)
# ─────────────────────────────────────────────────────────
@router.get("/charts/unemployment-age-trend")
async def get_unemployment_age_trend(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):
    rows = db.execute(text("""
        SELECT
            year_id AS year,
            age_group_label AS category,
            unemployment_pct AS value
        FROM gold.fact_unemployment_age
        WHERE unemployment_pct IS NOT NULL
        ORDER BY year_id, age_group_key
    """)).fetchall()

    return {
        "data": [
            {
                "year": int(r[0]),
                "category": str(r[1]),
                "value": float(r[2]),
            }
            for r in rows
            if r[0] is not None and r[1] is not None and r[2] is not None
        ]
    }


# ─────────────────────────────────────────────────────────
# Unemployment by Education Trend (Multi-line)
# ─────────────────────────────────────────────────────────
@router.get("/charts/unemployment-education-trend")
async def education(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):
    rows = db.execute(text("""
        SELECT
            year_id AS year,
            edu_label AS category,
            unemployment_pct AS value
        FROM gold.fact_unemployment_education
        WHERE unemployment_pct IS NOT NULL
        ORDER BY year_id, edu_key
    """)).fetchall()

    return {
        "data": [
            {
                "year": int(r[0]),
                "category": str(r[1]),
                "value": float(r[2]),
            }
            for r in rows
            if r[0] is not None and r[1] is not None and r[2] is not None
        ]
    }

# ─────────────────────────────────────────────────────────
# Total Unemployment Trend (Line Chart)
# ─────────────────────────────────────────────────────────
@router.get("/charts/total-unemployment-trend")
async def get_total_unemployment_trend(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db)
):
    rows = db.execute(text("""
        SELECT
            year_id AS year,
            total_unemployment_rate AS value
        FROM gold.fact_total_unemployment
        WHERE total_unemployment_rate IS NOT NULL
        ORDER BY year_id
    """)).fetchall()

    return {
        "data": [
            {
                "year": int(r[0]),
                "value": float(r[1])
            }
            for r in rows
            if r[0] is not None and r[1] is not None
        ]
    }

@router.get("/charts/long-run-education-effect")
async def get_long_run_education_effect(_: UserOut = Depends(get_current_user)):
    path = RESULTS_DIR / "rsui_long_run_unemployment_education.csv"

    print("DEBUG path:", path.resolve())
    print("DEBUG exists:", path.exists())

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Missing file: {path.resolve()}"
        )

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    print("DEBUG columns:", list(df.columns))

    required = {"edu_label", "long_run_effect", "n_obs", "aic", "bic"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Education long-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    df = df.rename(columns={
        "edu_label": "label",
        "long_run_effect": "value",
    })

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["n_obs"] = pd.to_numeric(df["n_obs"], errors="coerce")
    df["aic"] = pd.to_numeric(df["aic"], errors="coerce")
    df["bic"] = pd.to_numeric(df["bic"], errors="coerce")

    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=["label", "value"])

    df["abs_value"] = df["value"].abs()
    df = df.sort_values("abs_value", ascending=False).drop(columns=["abs_value"])

    return {
        "data": df[["label", "value", "n_obs", "aic", "bic"]].to_dict(orient="records")
}

@router.get("/charts/short-run-education-effect")
async def get_short_run_education_effect(_: UserOut = Depends(get_current_user)):
    path = RESULTS_DIR / "rsui_short_run_unemployment_education.csv"

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Missing file: {path.resolve()}"
        )

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"edu_label", "coef", "pvalue"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Education short-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    df = df.rename(columns={
        "edu_label": "label",
        "coef": "value",
        "pvalue": "p_value",
    })

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["p_value"] = pd.to_numeric(df["p_value"], errors="coerce")

    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=["label", "value", "p_value"])

    df["is_significant"] = df["p_value"] < 0.05
    df["abs_value"] = df["value"].abs()
    df = df.sort_values("abs_value", ascending=False).drop(columns=["abs_value"])

    return {
        "data": df[["label", "value", "p_value", "is_significant"]].to_dict(orient="records")
    }

@router.get("/charts/total-unemployment-longrun")
async def get_total_unemployment_longrun(_: UserOut = Depends(get_current_user)):

    path = RESULTS_DIR / "rsui_total_unemployment_long_run_effects.csv"

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    df = df.rename(columns={
        "tot_category_label": "label",
        "long_run_effect": "value"
    })

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["label", "value"])

    return {
        "data": [
            {
                "label": df.iloc[0]["label"],
                "value": float(df.iloc[0]["value"])
            }
        ]
    }

        
        
# ─────────────────────────────────────────────────────────
# RSUI Trend (Line Chart)
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

    if range == "10y":
        data = data[-10:]

    return {"data": data}





@router.get("/charts/unemployment-age-longrun")
async def get_unemployment_age_longrun(_: UserOut = Depends(get_current_user)):
    """
    Returns only long-run ARDL effects for unemployment-by-age vs RSUI.

    Output:
    {
      "data": [
        { "label": "...", "value": 0.123, "n_obs": 21, "aic": 300.1, "bic": 305.2 },
        ...
      ]
    }
    """

    long_path = RESULTS_DIR / "rsui_unemployment_by_age_long_run_effects.csv"

    if not long_path.exists():
        raise HTTPException(status_code=500, detail=f"Missing file: {long_path}")

    df = pd.read_csv(long_path)
    df.columns = [str(c).strip() for c in df.columns]

    # Required columns based on your CSV screenshot
    required = {"age_group_label", "long_run_effect", "n_obs", "aic", "bic"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Long-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    # Clean + map to frontend-friendly shape
    df = df.rename(columns={
        "age_group_label": "label",
        "long_run_effect": "value",
    })

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["n_obs"] = pd.to_numeric(df["n_obs"], errors="coerce")
    df["aic"] = pd.to_numeric(df["aic"], errors="coerce")
    df["bic"] = pd.to_numeric(df["bic"], errors="coerce")

    df["label"] = df["label"].astype(str).str.strip()
    df = df.dropna(subset=["label", "value"])

    # Sort by absolute effect (largest impact first)
    df["abs_value"] = df["value"].abs()
    df = df.sort_values("abs_value", ascending=False).drop(columns=["abs_value"])

    return {
        "data": df[["label", "value", "n_obs", "aic", "bic"]].to_dict(orient="records")
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