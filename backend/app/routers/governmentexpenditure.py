"""
Government Expenditure router – chart data and ARDL result endpoints
"""

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_warehouse_db
from app.models.schemas import UserOut
from app.routers.auth import get_current_user
from app.cache import cached_endpoint

BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = BASE_DIR / "results"

router = APIRouter()


# ─────────────────────────────────────────────────────────
# Government Expenditure by Type Trend (Multi-line)
# fact_gov_exp_by_type columns:
# year_id, exp_type_key, expenditure_rs_mn, exp_type_label
# ─────────────────────────────────────────────────────────
@router.get("/charts/expenditure-type-trend")
@cached_endpoint
async def get_expenditure_type_trend(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db),
):
    rows = db.execute(text("""
        SELECT
            year_id AS year,
            exp_type_label AS category,
            expenditure_rs_mn AS value
        FROM gold.fact_gov_exp_by_type
        WHERE expenditure_rs_mn IS NOT NULL
        ORDER BY year_id, exp_type_key
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
# Total Expenditure Trend (Line Chart)
# fact_total_expenditure columns:
# year_id, tot_exp_key, total_expenditure_rs_mn, category_label
# ─────────────────────────────────────────────────────────
@router.get("/charts/total-expenditure-trend")
@cached_endpoint
async def get_total_expenditure_trend(
    _: UserOut = Depends(get_current_user),
    db: Session = Depends(get_warehouse_db),
):
    rows = db.execute(text("""
        SELECT
            year_id AS year,
            total_expenditure_rs_mn AS value
        FROM gold.fact_total_expenditure
        WHERE total_expenditure_rs_mn IS NOT NULL
        ORDER BY year_id
    """)).fetchall()

    return {
        "data": [
            {
                "year": int(r[0]),
                "value": float(r[1]),
            }
            for r in rows
            if r[0] is not None and r[1] is not None
        ]
    }


# ─────────────────────────────────────────────────────────
# Long-run effect by expenditure type
# CSV: rsui_long_run_gov_exp_by_type.csv
# exp_type_label,n_obs,long_run_effect,aic,bic
# ─────────────────────────────────────────────────────────
@router.get("/charts/type-longrun-effect")
@cached_endpoint
async def get_type_longrun_effect(_: UserOut = Depends(get_current_user)):
    path = RESULTS_DIR / "rsui_long_run_gov_exp_by_type.csv"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.resolve()}")

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"exp_type_label", "n_obs", "long_run_effect", "aic", "bic"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Gov expenditure type long-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    df = df.rename(columns={
        "exp_type_label": "label",
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


# ─────────────────────────────────────────────────────────
# Short-run effect by expenditure type
# CSV: rsui_short_run_gov_exp_by_type.csv
# exp_type_label,n_obs,status,rsui_adf_p,x_adf_p,aic,bic,coef,pvalue
# ─────────────────────────────────────────────────────────
@router.get("/charts/type-shortrun-effect")
@cached_endpoint
async def get_type_shortrun_effect(_: UserOut = Depends(get_current_user)):
    path = RESULTS_DIR / "rsui_short_run_gov_exp_by_type.csv"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.resolve()}")

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"exp_type_label", "coef", "pvalue"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Gov expenditure type short-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    df = df.rename(columns={
        "exp_type_label": "label",
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


# ─────────────────────────────────────────────────────────
# Long-run effect for total expenditure
# CSV: rsui_long_run_total_expenditure.csv
# tot_category_label,n_obs,long_run_effect,aic,bic
# ─────────────────────────────────────────────────────────
@router.get("/charts/total-longrun-effect")
async def get_total_longrun_effect(_: UserOut = Depends(get_current_user)):
    path = RESULTS_DIR / "rsui_long_run_total_expenditure.csv"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.resolve()}")

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"tot_category_label", "n_obs", "long_run_effect", "aic", "bic"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Total expenditure long-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    df = df.rename(columns={
        "tot_category_label": "label",
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


# ─────────────────────────────────────────────────────────
# Short-run effect for total expenditure
# CSV: rsui_short_run_total_expenditure.csv
# tot_category_label,n_obs,status,rsui_adf_p,exp_adf_p,aic,bic,exp_coef,exp_pvalue
# ─────────────────────────────────────────────────────────
@router.get("/charts/total-shortrun-effect")
async def get_total_shortrun_effect(_: UserOut = Depends(get_current_user)):
    path = RESULTS_DIR / "rsui_short_run_total_expenditure.csv"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path.resolve()}")

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    required = {"tot_category_label", "exp_coef", "exp_pvalue"}
    missing = sorted(list(required - set(df.columns)))
    if missing:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Total expenditure short-run CSV schema mismatch",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            },
        )

    df = df.rename(columns={
        "tot_category_label": "label",
        "exp_coef": "value",
        "exp_pvalue": "p_value",
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


# ─────────────────────────────────────────────────────────
# Insights
# ─────────────────────────────────────────────────────────
@router.get("/insights")
@cached_endpoint
async def get_insights(_: UserOut = Depends(get_current_user)):
    return {
        "insights": [
            {
                "id": "govexp-1",
                "type": "warning",
                "icon": "💰",
                "title": "Government Spending Shift",
                "description": "Capital and recurrent expenditure trends can signal changing public investment priorities.",
            },
            {
                "id": "govexp-2",
                "type": "danger",
                "icon": "📉",
                "title": "Short-run Sensitivity",
                "description": "Short-run expenditure coefficients may indicate immediate RSUI responsiveness to spending changes.",
            },
            {
                "id": "govexp-3",
                "type": "success",
                "icon": "📊",
                "title": "Long-run Structural Impact",
                "description": "Long-run expenditure effects help reveal whether government spending has lasting influence on RSUI.",
            },
        ]
    }