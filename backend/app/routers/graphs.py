from __future__ import annotations

import math
import re
from fastapi import APIRouter, Query, HTTPException
from typing import Literal
from sqlalchemy import text, bindparam
from app.db import warehouse_engine
from app.cache import cached_endpoint

router = APIRouter()

# ---------------- Colors (same as yours) ----------------
PALETTE = [
    {"border": "rgba( 29,  78, 216, 1.0)", "background": "rgba( 29,  78, 216, 0.12)"},
    {"border": "rgba( 22, 163,  74, 1.0)", "background": "rgba( 22, 163,  74, 0.15)"},
    {"border": "rgba(147,  51, 234, 1.0)", "background": "rgba(147,  51, 234, 0.12)"},
    {"border": "rgba(234,  88,  12, 1.0)", "background": "rgba(234,  88,  12, 0.12)"},
    {"border": "rgba( 20, 184, 166, 1.0)", "background": "rgba( 20, 184, 166, 0.12)"},
    {"border": "rgba(244,  63,  94, 1.0)", "background": "rgba(244,  63,  94, 0.12)"},
    {"border": "rgba(245, 158,  11, 1.0)", "background": "rgba(245, 158,  11, 0.12)"},
    {"border": "rgba( 99, 102, 241, 1.0)", "background": "rgba( 99, 102, 241, 0.12)"},
]

# ---------------- DOMAIN REGISTRY ----------------
DOMAIN_REGISTRY: dict[str, dict] = {
    "gdp": {
        "fact_table": "gold.fact_gdp_sector_growth_annual",
        "dim_table": "gold.dim_gdp_sector",
        "join_key": "gdp_sector_key",
        "dim_label_col": "sector_name",
        "dim_code_col": "sector_code",
        "metric_col": "gdp_growth_pct",
        "year_col": "year_id",
        "y_label": "Annual Growth (%)",
        "title": "GDP Sector Growth",
        "display_name": "GDP Sector Growth",
    },

    "wages": {
        "fact_table": "gold.fact_wageindex_annual",
        "dim_table": "gold.dim_wagecategory",
        "join_key": "wage_category_key",
        "dim_label_col": "category_name",
        "dim_code_col": "category_code",
        "group_col": "category_group",   # ✅ allows filters by group
        "metric_col": "real_wage_index",
        "year_col": "year_id",
        "y_label": "Real Wage Index",
        "title": "Wage Trends",
        "display_name": "Wage Trends",
    },

    "gov_expenditure_by_type": {
        "fact_table": "gold.fact_gov_exp_by_type",
        "dim_table": "gold.dim_exp_type",
        "join_key": "exp_type_key",
        "dim_label_col": "exp_type_name",
        "dim_code_col": "exp_type_code",
        "metric_col": "expenditure_rs_mn",
        "year_col": "year_id",
        "y_label": "Expenditure (Rs Mn)",
        "title": "Government Expenditure by Type",
        "display_name": "Gov. Expenditure by Type",
    },

    "total_expenditure": {
        "fact_table": "gold.fact_total_expenditure",
        "dim_table": "gold.dim_tot_exp",
        "join_key": "tot_exp_key",
        "dim_label_col": "label",
        "dim_code_col": "label",
        "metric_col": "total_expenditure_rs_mn",
        "year_col": "year_id",
        "y_label": "Total Expenditure (Rs Mn)",
        "title": "Total Government Expenditure",
        "display_name": "Total Government Expenditure",
    },

    "pce": {
        "fact_table": "gold.fact_pce",
        "dim_table": "gold.dim_pce_category",
        "join_key": "category_id",
        "dim_label_col": "category_name",
        "dim_code_col": "category_code",
        "year_col": "year_id",
        "metric_col": "pce_percentage",
        "y_label": "PCE (%)",
        "title": "Personal Consumption Expenditure",
        "display_name": "PCE by Category",
        "metric_cols": {  # ✅ metric switching
            "default": "pce_percentage",
            "percentage": "pce_percentage",
            "actual": "pce_actual_value",
            "growth_rate": "pce_growth_rate",
            "growth_value": "pce_growth_value",
        },
    },

    "unemployment_education": {
        "fact_table": "gold.fact_unemployment_education",
        "dim_table": "gold.dim_education_level",
        "join_key": "edu_key",
        "dim_label_col": "edu_name",
        "dim_code_col": "edu_code",
        "metric_col": "unemployment_pct",
        "year_col": "year_id",
        "y_label": "Unemployment (%)",
        "title": "Unemployment by Education",
        "display_name": "Unemployment by Education",
    },

    "unemployment_age": {
        "fact_table": "gold.fact_unemployment_age",
        "dim_table": "gold.dim_age_group",
        "join_key": "age_group_key",
        "dim_label_col": "age_group_name",
        "dim_code_col": "age_group_code",
        "metric_col": "unemployment_pct",
        "year_col": "year_id",
        "y_label": "Unemployment (%)",
        "title": "Unemployment by Age Group",
        "display_name": "Unemployment by Age Group",
    },

    "total_unemployment": {
        "fact_table": "gold.fact_total_unemployment",
        "dim_table": "gold.dim_tot_unemployment",
        "join_key": "tot_unemp_key",
        "dim_label_col": "label",
        "dim_code_col": "label",
        "metric_col": "total_unemployment_rate",
        "year_col": "year_id",
        "y_label": "Unemployment Rate (%)",
        "title": "Total Unemployment",
        "display_name": "Total Unemployment",
    },

    # ✅ FAO: multi-dim joins
    "fao_sl": {
        "fact_table": "gold.fact_fao_sl",
        "year_col": "year",
        "metric_col": "value",
        "title": "FAO Sri Lanka Time Series",
        "display_name": "FAO Agriculture Data",
        "y_label": "Value",
        "default_series": {"fact_key": "item_id", "label_col": "item_name", "code_col": "item_code"},
        "joins": [
            {"fact_key": "domain_id",  "dim_table": "gold.dim_fao_domain",  "dim_key": "domain_id",  "dim_code_col": "domain_code",  "dim_label_col": "domain_name"},
            {"fact_key": "element_id", "dim_table": "gold.dim_fao_element", "dim_key": "element_id", "dim_code_col": "element_code", "dim_label_col": "element_name"},
            {"fact_key": "item_id",    "dim_table": "gold.dim_fao_item",    "dim_key": "item_id",    "dim_code_col": "item_code",    "dim_label_col": "item_name"},
            {"fact_key": "unit_id",    "dim_table": "gold.dim_fao_unit",    "dim_key": "unit_id",    "dim_code_col": "unit_name",    "dim_label_col": "unit_name"},
        ],
    },
}

# ---------------- tiny helpers ----------------
def safe_float(x):
    if x is None:
        return None
    try:
        v = float(x)
    except Exception:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def parse_filters(filters: list[str] | None) -> list[tuple[str, str]]:
    """
    filters=["category_group:Sectoral","category_code:central_govt_employees"]
    -> {"category_group":"Sectoral","category_code":"central_govt_employees"}
    """
    out: list[tuple[str, str]] = []
    if not filters:
        return out
    for f in filters:
        if ":" not in f:
            raise HTTPException(400, f"Bad filter '{f}'. Use key:value")
        k, v = f.split(":", 1)
        out.append((k.strip(), v.strip()))
    return out


def _normalize_phrase(value: str) -> str:
    value = value.lower().replace("&", " and ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+ ]", " ", value)).strip()


def _tokenize_for_match(value: str) -> set[str]:
    stop = {"and", "in", "of", "for", "the", "a", "an"}
    return {tok for tok in _normalize_phrase(value).split(" ") if tok and tok not in stop}


def _canonicalize_subsector_term(domain: str, term: str) -> str:
    t = _normalize_phrase(term)
    t = re.sub(r"\b(graph|chart|plot|line|bar|area)\b", " ", t)
    t = re.sub(r"\b(in|of|for)\s+(a|an|the)\b", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    if domain == "gdp":
        if re.search(r"\bagri|agriculture|farming|farm\b", t):
            return "agriculture"
        if re.search(r"\bindustry|industrial|manufactur", t):
            return "industry"
        if re.search(r"\bservice|services\b", t):
            return "services"
        t = re.sub(r"\b(gdp|growth|rate|sector|annual|sri lanka)\b", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    if domain == "wages":
        if re.search(r"\bcentral\b.*\b(govt|government)\b", t):
            return "central govt employees"
        if re.search(r"\bindustry|commerce\b", t):
            return "workers in industry and commerce"
        if re.search(r"\bagri|agriculture|farming|farm\b", t):
            return "workers in agriculture"
        if re.search(r"\bservice|services\b", t):
            return "workers in services"
        if re.search(r"\bwages?\s+boards?\b", t):
            return "all wages boards trades"
        t = re.sub(r"\b(wage|wages|index|worker|workers)\b", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    if domain == "gov_expenditure_by_type":
        if re.search(r"\bcapital\b", t):
            return "capital expenditure"
        if re.search(r"\brecurrent\b", t):
            return "recurrent expenditure"
        t = re.sub(r"\b(expenditure|spending|type|gov|government)\b", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    if domain == "pce":
        if re.search(r"\bclothing\b.*\bfootwear\b|\bfootwear\b.*\bclothing\b", t):
            return "clothing and footwear"
        if re.search(r"\bcommunication\b", t):
            return "information and communication"
        if re.search(r"\btransport\b", t):
            return "transport"
        t = re.sub(r"\b(pce|percentage|consumption|expenditure|category)\b", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    if domain == "unemployment_education":
        if re.search(r"\bgce\b.*\bo\b.*\bl\b|\bo\s*/?\s*l\b|ordinary level", t):
            return "gce o/l"
        if re.search(r"\bgce\b.*\ba\b.*\bl\b|\ba\s*/?\s*l\b|advanced level", t):
            return "gce a/l"
        t = re.sub(r"\b(unemployment|education|level|among|by)\b", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    if domain == "unemployment_age":
        plus_m = re.search(r"\b(\d{1,2})\s*(?:\+|plus|and above|and over)(?:\b|$)", t)
        if plus_m:
            return f"{plus_m.group(1)}+"
        range_m = re.search(r"\b(\d{1,2})\s*(?:to\s*)?(\d{1,2})\b", t)
        if range_m:
            return f"{range_m.group(1)}-{range_m.group(2)}"
        t = re.sub(r"\b(unemployment|age|group|among|by)\b", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    return t


def _resolve_standard_subsectors(cfg: dict, domain: str, subsectors: list[str]) -> list[str]:
    dt = cfg["dim_table"]
    cc = cfg["dim_code_col"]
    lc = cfg["dim_label_col"]
    sql = text(f"SELECT DISTINCT {cc}::text AS code, {lc}::text AS label FROM {dt}")
    with warehouse_engine.connect() as conn:
        rows = conn.execute(sql).fetchall()

    options: list[tuple[str, str, str]] = []
    for code, label in rows:
        code_s = (code or "").strip()
        label_s = (label or "").strip()
        if not code_s and not label_s:
            continue
        options.append((code_s, label_s, _normalize_phrase(label_s)))

    resolved: list[str] = []
    for raw in subsectors:
        if not raw:
            continue
        target = _canonicalize_subsector_term(domain, raw)
        if not target:
            continue

        # Prefer strict semantic matching for education levels to avoid
        # A/L <-> O/L confusion from fuzzy token overlap.
        if domain == "unemployment_education":
            def _edu_bucket(v: str) -> str | None:
                n = _normalize_phrase(v)
                if re.search(r"\bgce\b.*\ba\b.*\bl\b|\ba\s*/?\s*l\b|advanced level|\bhnce\b|\babove\b", n):
                    return "a_l"
                if re.search(r"\bgce\b.*\bo\b.*\bl\b|\bo\s*/?\s*l\b|ordinary level|\bncge\b", n):
                    return "o_l"
                if re.search(r"\bgrade\s*6\s*(?:-|to)?\s*10\b|\b6\s*(?:-|to)\s*10\b", n):
                    return "grade_6_10"
                if re.search(r"\bgrade\s*5\b|\b5\s*and below\b|\bbelow\b", n):
                    return "grade_5_below"
                return None

            target_bucket = _edu_bucket(target)
            if target_bucket:
                strict = next(
                    (
                        label
                        for code, label, _ in options
                        if _edu_bucket(code) == target_bucket or _edu_bucket(label) == target_bucket
                    ),
                    None,
                )
                if strict:
                    resolved.append(strict)
                    continue

        target_n = _normalize_phrase(target)
        exact = next(
            (
                label
                for code, label, label_n in options
                if _normalize_phrase(code) == target_n or label_n == target_n
            ),
            None,
        )
        if exact:
            resolved.append(exact)
            continue

        contains = next(
            (
                label
                for _, label, label_n in options
                if target_n in label_n or label_n in target_n
            ),
            None,
        )
        if contains:
            resolved.append(contains)
            continue

        target_tokens = _tokenize_for_match(target_n)
        if target_tokens:
            scored = []
            for _, label, label_n in options:
                label_tokens = _tokenize_for_match(label_n)
                overlap = len(target_tokens.intersection(label_tokens))
                if overlap > 0:
                    scored.append((overlap, label))
            if scored:
                scored.sort(key=lambda x: x[0], reverse=True)
                resolved.append(scored[0][1])
                continue

        raise HTTPException(400, f"Unknown subsector '{raw}' for domain '{domain}'")

    # dedupe while preserving order
    out: list[str] = []
    seen: set[str] = set()
    for value in resolved:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def build_graph_query_params(user_text: str) -> dict:
    params: dict = {}
    text_l = user_text.lower()

    compare_match = re.search(
        r"\bcompare\s+(.+?)\s+and\s+(.+?)(?:\s+(?:graph|chart|index)\b|[.?!,]|$)",
        user_text,
        flags=re.IGNORECASE,
    )
    if compare_match:
        left = compare_match.group(1).strip()
        right = compare_match.group(2).strip()
        if "gdp" in text_l:
            params["domain"] = "gdp"
            params["subsectors"] = [left, right]
        elif "wage" in text_l:
            params["domain"] = "wages"
            params["subsectors"] = [left, right]

    if ("unemployment_age" in text_l or "unemployment age" in text_l) and (
        "40+" in text_l or "40 plus" in text_l
    ):
        params["domain"] = "unemployment_age"
        params["subsector"] = "40+"

    if "fao" in text_l and "rice" in text_l:
        params["domain"] = "fao_sl"
        params.setdefault("filters", [])
        params["filters"].append("item_name:Rice")

    return params


def rows_to_chart(rows: list, chart_type: str):
    series = {}
    for y, label, val in rows:
        y = int(y)
        label = str(label)
        val = safe_float(val)
        series.setdefault(label, {})
        series[label][y] = val

    years = sorted({y for s in series.values() for y in s.keys()})
    labels = [str(y) for y in years]

    datasets = []
    for idx, (name, mapping) in enumerate(series.items()):
        c = PALETTE[idx % len(PALETTE)]
        data = [mapping.get(y) for y in years]
        ds = {
            "label": name,
            "data": data,
            "borderColor": c["border"],
            "backgroundColor": c["background"],
            "borderWidth": 2,
            "tension": 0.35,
            "pointRadius": 3,
            "pointHoverRadius": 6,
            "spanGaps": True,
        }
        if chart_type == "bar":
            ds.pop("tension", None)
            ds.pop("pointRadius", None)
            ds.pop("pointHoverRadius", None)
            ds.pop("spanGaps", None)
        datasets.append(ds)

    return labels, datasets


# ---------------- SQL fetchers ----------------
def _fetch_standard(
    domain: str,
    cfg: dict,
    subsector_code: str | None,
    year_from: int | None,
    year_to: int | None,
    metric_col_override: str | None = None,
    filters: list[tuple[str, str]] | None = None,
    subsectors: list[str] | None = None,   # ✅ NEW
) -> list:
    ft = cfg["fact_table"]
    dt = cfg["dim_table"]
    jk = cfg["join_key"]
    lc = cfg["dim_label_col"]
    cc = cfg["dim_code_col"]
    mc = metric_col_override or cfg["metric_col"]
    yc = cfg["year_col"]

    clauses: list[str] = []
    params: dict = {}
    use_in = False

    if year_from is not None:
        clauses.append(f"f.{yc} >= :year_from")
        params["year_from"] = year_from
    if year_to is not None:
        clauses.append(f"f.{yc} <= :year_to")
        params["year_to"] = year_to

    # old single subsector (kept)
    if subsector_code and subsector_code.lower() != "all":
        clauses.append(
            f"(LOWER(d.{cc}::text) = LOWER(:subsector_code) OR LOWER(d.{lc}::text) = LOWER(:subsector_code))"
        )
        params["subsector_code"] = subsector_code

    # ✅ NEW: multiple subsectors (for compare)
    if subsectors:
        subsectors = _resolve_standard_subsectors(cfg, domain, subsectors)
        clauses.append(f"(LOWER(d.{cc}::text) IN :subs OR LOWER(d.{lc}::text) IN :subs)")
        params["subs"] = [s.lower() for s in subsectors]
        use_in = True

    # filters (dim columns only)
    allowed = {cfg.get("dim_code_col"), cfg.get("dim_label_col")}
    if "group_col" in cfg:
        allowed.add(cfg["group_col"])
    allowed = {x for x in allowed if x}

    if filters:
        for idx, (k, v) in enumerate(filters):
            if k not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid filter key '{k}'. Allowed: {sorted(list(allowed))}",
                )
            p = f"f_{k}_{idx}"
            clauses.append(f"LOWER(d.{k}::text) = LOWER(:{p})")
            params[p] = v

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    q = text(f"""
        SELECT
            f.{yc}   AS year,
            d.{lc}   AS series_label,
            f.{mc}   AS metric_value
        FROM {ft} f
        JOIN {dt} d ON d.{jk} = f.{jk}
        {where}
        ORDER BY series_label, f.{yc}
    """)

    # ✅ required for IN :subs
    if use_in:
        q = q.bindparams(bindparam("subs", expanding=True))

    with warehouse_engine.connect() as conn:
        return conn.execute(q, params).fetchall()


def fetch_fao(cfg, subsector, year_from, year_to, filters_list):
    joins = cfg["joins"]
    yc, mc = cfg["year_col"], cfg["metric_col"]
    ds = cfg["default_series"]

    # build joins + aliases
    alias_map = {}
    join_sql = []
    for j in joins:
        alias = j["dim_table"].split(".")[-1]
        alias_map[j["fact_key"]] = alias
        join_sql.append(f"LEFT JOIN {j['dim_table']} {alias} ON {alias}.{j['dim_key']} = f.{j['fact_key']}")

    series_alias = alias_map[ds["fact_key"]]
    label_expr = f"{series_alias}.{ds['label_col']}"
    code_expr = f"{series_alias}.{ds['code_col']}"

    clauses, params = [], {}

    if year_from is not None:
        clauses.append(f"f.{yc} >= :yf")
        params["yf"] = year_from
    if year_to is not None:
        clauses.append(f"f.{yc} <= :yt")
        params["yt"] = year_to

    if subsector:
        clauses.append(f"LOWER({code_expr}::text) = LOWER(:sub)")
        params["sub"] = subsector

    # FAO allowed filters (simple fixed list)
    # keys user can send -> (fact_key, col_name)
    allowed = {
        "domain_code": ("domain_id", "domain_code"),
        "domain_name": ("domain_id", "domain_name"),
        "element_code": ("element_id", "element_code"),
        "element_name": ("element_id", "element_name"),
        "item_code": ("item_id", "item_code"),
        "item_name": ("item_id", "item_name"),
        "unit_name": ("unit_id", "unit_name"),
    }

    for idx, (k, v) in enumerate(filters_list or []):
        if k not in allowed:
            raise HTTPException(400, f"FAO filter '{k}' not allowed. Allowed: {sorted(list(allowed.keys()))}")
        fact_key, col = allowed[k]
        alias = alias_map[fact_key]
        p = f"fao_{k}_{idx}"
        if k.endswith("_name"):
            clauses.append(f"LOWER({alias}.{col}::text) LIKE LOWER(:{p})")
            params[p] = f"%{v}%"
        else:
            clauses.append(f"LOWER({alias}.{col}::text) = LOWER(:{p})")
            params[p] = v

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    sql = text(f"""
        SELECT f.{yc} AS year, {label_expr} AS series_label, f.{mc} AS metric_value
        FROM {cfg['fact_table']} f
        {" ".join(join_sql)}
        {where}
        ORDER BY series_label, f.{yc}
    """)
    with warehouse_engine.connect() as conn:
        return conn.execute(sql, params).fetchall()


# ---------------- endpoints ----------------
@router.get("/domains")
@cached_endpoint
def list_domains():
    return {
        "domains": [
            {
                "key": k,
                "display_name": cfg.get("display_name", k),
                "title": cfg.get("title", k),
                "y_label": cfg.get("y_label", "Value"),
                "is_multi_dim": "joins" in cfg,
                "metric_options": list(cfg["metric_cols"].keys()) if "metric_cols" in cfg else None,
            }
            for k, cfg in DOMAIN_REGISTRY.items()
        ]
    }


@router.get("/subsectors")
@cached_endpoint
def get_subsectors(
    domain: str = Query(...),
    field: str | None = Query(None, description="For wages: field=category_group to list groups"),
):
    cfg = DOMAIN_REGISTRY.get(domain)
    if not cfg:
        raise HTTPException(404, f"Unknown domain '{domain}'")

    # standard domains
    if "joins" not in cfg:
        dt = cfg["dim_table"]
        if field:
            # allow listing category_group for wages
            allowed = {cfg["dim_code_col"], cfg["dim_label_col"]}
            if "group_col" in cfg:
                allowed.add(cfg["group_col"])
            if field not in allowed:
                raise HTTPException(400, f"field must be one of {sorted(list(allowed))}")
            sql = text(f"SELECT DISTINCT {field}::text, {field}::text FROM {dt} ORDER BY {field}::text")
        else:
            cc, lc = cfg["dim_code_col"], cfg["dim_label_col"]
            sql = text(f"SELECT DISTINCT {cc}::text, {lc} FROM {dt} ORDER BY {lc}")
        with warehouse_engine.connect() as conn:
            rows = conn.execute(sql).fetchall()
        return {"domain": domain, "subsectors": [{"code": str(r[0]), "name": str(r[1])} for r in rows]}

    # FAO: default series list (items)
    ds = cfg["default_series"]
    join = next(j for j in cfg["joins"] if j["fact_key"] == ds["fact_key"])
    sql = text(f"SELECT DISTINCT {ds['code_col']}::text, {ds['label_col']} FROM {join['dim_table']} ORDER BY {ds['label_col']}")
    with warehouse_engine.connect() as conn:
        rows = conn.execute(sql).fetchall()
    return {"domain": domain, "subsectors": [{"code": str(r[0]), "name": str(r[1])} for r in rows]}


@router.get("/timeseries")
@cached_endpoint
def timeseries(
    domain: str = Query(...),
    subsector: str = Query("all"),
    subsectors: list[str] | None = Query(None, description="Repeat: subsectors=AGR&subsectors=IND"),
    year_from: int | None = Query(None),
    year_to: int | None = Query(None),
    type: Literal["line", "bar", "area"] = Query("line"),
    metric: str = Query("default"),
    filters: list[str] | None = Query(None, description="Repeatable: filters=key:value"),
):
    cfg = DOMAIN_REGISTRY.get(domain)
    if not cfg:
        raise HTTPException(404, f"Unknown domain '{domain}'")

    sub = None if (not subsector or subsector.lower() == "all") else subsector
    filters_list = parse_filters(filters)

    # metric override for domains like pce
    metric_override = None
    if "metric_cols" in cfg:
        if metric not in cfg["metric_cols"]:
            raise HTTPException(400, f"Unknown metric '{metric}'. Allowed: {sorted(list(cfg['metric_cols'].keys()))}")
        metric_override = cfg["metric_cols"][metric]

    # FAO requires at least one filter OR subsector
    if domain == "fao_sl" and (not sub) and (not filters_list):
        raise HTTPException(400, "FAO needs at least one filter. Example: filters=item_name:Rice")

    applied_filters = filters_list

    # fetch rows
    if "joins" in cfg:
        rows = fetch_fao(cfg, sub, year_from, year_to, filters_list)
        # FAO fallback: if unit filter is too restrictive, retry without it.
        if (not rows) and domain == "fao_sl" and filters_list:
            relaxed_filters = [(k, v) for (k, v) in filters_list if k != "unit_name"]
            if relaxed_filters and len(relaxed_filters) < len(filters_list):
                rows = fetch_fao(cfg, sub, year_from, year_to, relaxed_filters)
                if rows:
                    applied_filters = relaxed_filters
    else:
        rows = _fetch_standard(
            domain,
            cfg,
            sub,
            year_from,
            year_to,
            metric_col_override=metric_override,
            filters=filters_list,
            subsectors=subsectors,
        )

    if not rows:
        raise HTTPException(404, "No data found for given filters.")

    chart_type = "bar" if type == "bar" else "line"
    labels, datasets = rows_to_chart(rows, chart_type)

    if type == "area":
        for ds in datasets:
            ds["fill"] = True

    title = cfg.get("title", domain)
    if labels:
        title = f"{title} ({labels[0]}–{labels[-1]})"

    return {
        "domain": domain,
        "chart_type": chart_type,
        "title": title,
        "labels": labels,
        "datasets": datasets,
        "y_axis_label": cfg.get("y_label", "Value"),
        "applied_filters": applied_filters,
        "applied_subsectors": subsectors,
        "metric": metric,
    }


@router.get("/available")
@cached_endpoint
def available():
    return list_domains()
