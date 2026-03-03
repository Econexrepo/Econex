"""
Econex AI Service – relationship-table driven response engine (no OpenAI required).

Uses relationship_table.csv (with group_type) and answers questions by:
- extracting indep_var / horizon / group_type / group_label hints
- retrieving matching rows
- producing a natural-language decision-friendly response
- ranking "most affecting" categories when asked
"""

import pathlib
import re
from typing import Optional, List, Dict

import pandas as pd


# ── Relationship table loading ────────────────────────────────────────────────
_BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent  # Econex repo root

_CANDIDATES = [
    _BASE_DIR / "relationship_table.csv",  # ✅ your current location (repo root)
]


def _load_relationship_table() -> pd.DataFrame:
    for path in _CANDIDATES:
        if path.exists():
            df = pd.read_csv(path)
            print(f"[ai_service] Loaded relationship_table.csv from: {path} — {len(df)} rows")

            required = {"dep_var", "indep_var", "group_type", "group_label", "horizon", "description"}
            missing = required - set(df.columns)
            if missing:
                raise ValueError(f"relationship_table.csv missing columns: {sorted(missing)}")

            # Normalize to strings for safe matching
            for c in ["dep_var", "indep_var", "group_type", "group_label", "horizon", "description", "source_file", "status"]:
                if c in df.columns:
                    df[c] = df[c].astype(str)

            # Numeric columns (safe coercion)
            for c in ["effect_value", "pvalue", "aic", "bic", "n_obs"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")

            # Lowercase helper columns
            df["_dep_l"] = df["dep_var"].str.lower()
            df["_indep_l"] = df["indep_var"].str.lower()
            df["_gtype_l"] = df["group_type"].str.lower()
            df["_glabel_l"] = df["group_label"].str.lower()
            df["_horizon_l"] = df["horizon"].str.lower()

            return df

    raise FileNotFoundError(
        "[ai_service] Could not find relationship_table.csv. "
        "Put it in the project root as relationship_table.csv."
    )


_REL = _load_relationship_table()


# ── NLP helpers ───────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _wants_details(q: str) -> bool:
    qn = _norm(q)
    return any(k in qn for k in [
        "show details", "details", "numbers", "stats", "statistics",
        "p value", "p-value", "coef", "coefficient", "aic", "bic"
    ])


def _extract_horizon(q: str) -> Optional[str]:
    qn = _norm(q)
    if "long run" in qn or "long-run" in qn or "longrun" in qn:
        return "long_run"
    if "short run" in qn or "short-run" in qn or "shortrun" in qn:
        return "short_run"
    return None


def _default_horizon_if_relationship(q: str) -> Optional[str]:
    """
    If user says 'relationship/association/effect/impact/link' and does NOT
    specify short/long run, default to long_run.
    """
    qn = _norm(q)
    if any(k in qn for k in ["relationship", "relation", "association", "link", "impact", "effect", "influence"]):
        return "long_run"
    return None


def _extract_indep(q: str) -> Optional[str]:
    """
    Map user words -> indep_var values in relationship_table.csv
    Includes the typo 'expanditure' support.
    """
    qn = _norm(q)

    synonyms = {
        "unemployment": ["unemployment", "jobless", "joblessness"],
        "government_expenditure": [
            "government expenditure", "gov expenditure", "gov exp", "government exp",
            "government spending", "public spending", "public expenditure",
            "state spending", "state expenditure", "fiscal spending", "gov spending",
            # ✅ typo support
            "government expanditure", "public expanditure", "expanditure"
        ],
        "total_expenditure": ["total expenditure", "total government expenditure", "total gov expenditure", "overall expenditure"],
        "wage": ["wage", "wages", "salary", "salaries"],
        "gdp": ["gdp"],
        "pce": ["pce", "consumption", "personal consumption", "consumption expenditure"],
    }

    for indep, keys in synonyms.items():
        if any(k in qn for k in keys):
            return indep

    # fallback: if user types exact indep_var
    for v in sorted(set(_REL["_indep_l"].tolist())):
        if v and v in qn:
            return v

    return None


def _is_compare_intent(q: str) -> bool:
    qn = _norm(q)
    return any(w in qn for w in [
        "compare", "comparison", "rank", "ranking",
        "top", "best", "worst", "highest", "lowest",
        "strongest", "largest", "smallest"
    ])


def _is_top_impact_intent(q: str) -> bool:
    qn = _norm(q)
    return any(w in qn for w in [
        "mostly affect", "affect the most", "affects the most",
        "most affect", "most impact", "highest impact", "strongest impact",
        "biggest impact", "which category", "which categories",
        "which age group", "which age groups",
        "which education", "which education levels",
        "top categories", "top category", "top groups", "top group",
        "rank categories", "rank groups",
        "strongest effect", "largest effect"
    ])


def _extract_group_type(q: str, indep: Optional[str]) -> Optional[str]:
    """
    Match to your ACTUAL group_type values in relationship_table.csv:
    - age_group
    - edu
    - exp_type
    - category
    - category_name
    - sector_name
    """
    qn = _norm(q)

    if "age" in qn:
        return "age_group"

    if "education" in qn or "edu" in qn:
        return "edu"

    # capital/recurrent are exp_type in your table
    if "capital" in qn or "recurrent" in qn or "exp type" in qn or "expenditure type" in qn:
        return "exp_type"

    if "sector" in qn:
        return "sector_name"

    # category intent depends on variable
    if "category" in qn or "categories" in qn or "by category" in qn:
        if indep == "wage":
            return "category_name"   # wages by category
        return "category"            # pce categories + unemployment(total) category

    return None


def _humanize_indep(indep: str) -> str:
    mapping = {
        "unemployment": "unemployment",
        "government_expenditure": "government expenditure",
        "total_expenditure": "total government expenditure",
        "wage": "wages",
        "gdp": "GDP",
        "pce": "PCE (consumption expenditure)",
        "x": "the variable",
    }
    key = (indep or "").strip().lower()
    return mapping.get(key, key.replace("_", " "))


def _humanize_group_label(group_label: str) -> str:
    g = (group_label or "").strip()
    if not g:
        return "the overall sample"
    gl = g.replace("_", " ").strip()

    # nicer age formatting if needed
    gl2 = gl.lower()
    gl2 = re.sub(r"(age)\s*(\d{1,2})[\s\-_]*(\d{1,2})", r"age group \2–\3", gl2)
    return gl2


def _format_details(row: dict) -> str:
    parts = []
    if pd.notna(row.get("effect_value", float("nan"))):
        parts.append(f"effect={row['effect_value']:.6g}")
    if pd.notna(row.get("pvalue", float("nan"))):
        parts.append(f"p={row['pvalue']:.3g}")
    if pd.notna(row.get("aic", float("nan"))):
        parts.append(f"AIC={row['aic']}")
    if pd.notna(row.get("bic", float("nan"))):
        parts.append(f"BIC={row['bic']}")
    if pd.notna(row.get("n_obs", float("nan"))):
        parts.append(f"n={int(row['n_obs'])}")
    if row.get("source_file"):
        parts.append(f"source={row['source_file']}")
    return " | ".join(parts)


def naturalize_row(row: dict, show_stats: bool = False) -> str:
    indep_key = str(row.get("indep_var", "x"))
    indep = _humanize_indep(indep_key)

    group = _humanize_group_label(str(row.get("group_label", "")))
    horizon = str(row.get("horizon", "")).replace("_", " ").strip().lower() or "result"

    coef = row.get("effect_value", float("nan"))
    pval = row.get("pvalue", float("nan"))

    # Direction + plain takeaway
    if pd.notna(coef) and coef > 0:
        direction = "RSUI tends to go **up**"
        takeaway = f"When **{indep}** increases, RSUI increases (for **{group}**)."
        decision = f"If the goal is to reduce RSUI, this model suggests **reducing {indep}** (for **{group}**)."
    elif pd.notna(coef) and coef < 0:
        direction = "RSUI tends to go **down**"
        takeaway = f"When **{indep}** increases, RSUI decreases (for **{group}**)."
        # Avoid giving weird recommendations like "increase unemployment"
        if indep_key.lower() == "unemployment":
            decision = "This direction can be counterintuitive for unemployment; treat it as model-based correlation and validate with more checks."
        else:
            decision = f"If the goal is to reduce RSUI, this model suggests **increasing {indep}** would be associated with lower RSUI (interpret carefully)."
    else:
        direction = "there is **no clear direction**"
        takeaway = f"No clear direction between **{indep}** and RSUI (for **{group}**)."
        decision = "Treat this as weak/unclear evidence."

    # Confidence
    if pd.notna(pval):
        if pval < 0.01:
            conf = "High confidence (statistically strong)."
        elif pval < 0.05:
            conf = "Moderate confidence (statistically significant)."
        else:
            conf = "Low confidence (not statistically strong)."
    else:
        conf = "Confidence unknown (p-values not provided in this result file)."

    if "low confidence" in conf.lower() or "unknown" in conf.lower():
        decision2 = "Decision tip: use this as **directional** insight and confirm with diagnostics / additional models."
    else:
        decision2 = f"Decision tip: {decision}"

    msg = (
        f"**{horizon.title()} insight**\n"
        f"- For **{group}**, {direction} when **{indep}** changes.\n"
        f"- Confidence: **{conf}**\n"
        f"- {decision2}\n"
        f"- Plain takeaway: **{takeaway}**"
    )

    if show_stats:
        details = _format_details(row)
        if details:
            msg += f"\n\n**Details:** {details}"
    else:
        msg += "\n\n(If you want the numbers, say **show details**.)"

    return msg


# ── Retrieval / ranking ───────────────────────────────────────────────────────
def _filter(dep: str = "rsui",
            indep: Optional[str] = None,
            horizon: Optional[str] = None,
            group_type: Optional[str] = None,
            group_hint: Optional[str] = None) -> pd.DataFrame:
    df = _REL[_REL["_dep_l"] == dep.lower()].copy()

    if indep:
        df = df[df["_indep_l"] == indep.lower()]
    if horizon:
        df = df[df["_horizon_l"] == horizon.lower()]
    if group_type:
        df = df[df["_gtype_l"] == group_type.lower()]
    if group_hint:
        gh = _norm(group_hint)
        df = df[df["_glabel_l"].apply(lambda x: gh in _norm(x))]

    return df


def _rank_most_affecting(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    out = df.copy()
    out["abs_effect"] = out["effect_value"].abs()

    out["sig_flag"] = out["pvalue"].apply(lambda p: 1 if pd.notna(p) and p < 0.05 else 0)
    out = out.sort_values(["sig_flag", "abs_effect"], ascending=[False, False], na_position="last")
    return out.head(k)


def _help_text() -> str:
    indeps = ", ".join(sorted(set(_REL["indep_var"].str.lower())))
    gtypes = ", ".join(sorted(set(_REL["group_type"].str.lower())))
    horizons = ", ".join(sorted(set(_REL["horizon"].str.lower())))
    return (
        "Try asking:\n"
        "- relationship between government expenditure and rsui\n"
        "- relationship between gov spending and rsui short run capital\n"
        "- compare government expenditure long run\n"
        "- which age groups mostly affect rsui for unemployment\n"
        "- top education categories affecting rsui unemployment\n"
        "- which pce categories affect rsui the most\n"
        "- wages by category strongest impact\n\n"
        f"Available variables: {indeps}\n"
        f"Available group types: {gtypes}\n"
        f"Available horizons: {horizons}"
    )


# ── Main function used by router ──────────────────────────────────────────────
def get_ai_response(message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
    q = message or ""
    qn = _norm(q)

    indep = _extract_indep(q)
    horizon = _extract_horizon(q) or _default_horizon_if_relationship(q)
    show_stats = _wants_details(q)

    group_type = _extract_group_type(q, indep)

    # Group label hint: keep remaining tokens as a weak substring hint
    cleaned = qn
    for token in [
        "rsui", "relationship", "relation", "association", "link", "impact", "effect", "influence",
        "between", "and", "with", "vs", "versus",
        "long run", "long-run", "short run", "short-run",
        "compare", "comparison", "rank", "ranking",
        "top", "best", "worst", "highest", "lowest", "strongest",
        "show details", "details", "numbers", "stats", "statistics",
        "mostly affect", "affect the most", "most impact", "highest impact", "strongest impact",
        "which category", "which categories", "which age group", "which age groups", "which education"
    ]:
        cleaned = cleaned.replace(token, " ")

    # remove indep synonyms (keep conservative; don't strip "capital"/"recurrent")
    for token in [
        "unemployment", "jobless",
        "government expenditure", "gov expenditure", "gov exp", "government spending", "public spending", "public expenditure",
        "government expanditure", "public expanditure", "expanditure",
        "total expenditure", "wage", "salary", "gdp", "pce", "consumption"
    ]:
        cleaned = cleaned.replace(token, " ")

    group_hint = _norm(cleaned)
    if len(group_hint) < 2:
        group_hint = None

    # Initial filter
    df = _filter(dep="rsui", indep=indep, horizon=horizon, group_type=group_type, group_hint=group_hint)

    # Relax group_hint first
    if df.empty and group_hint:
        df = _filter(dep="rsui", indep=indep, horizon=horizon, group_type=group_type, group_hint=None)

    # Relax group_type if mismatch
    if df.empty and group_type:
        df = _filter(dep="rsui", indep=indep, horizon=horizon, group_type=None, group_hint=group_hint)

    # Relax horizon if still empty
    if df.empty and horizon:
        df = _filter(dep="rsui", indep=indep, horizon=None, group_type=group_type, group_hint=group_hint)

    if df.empty:
        return "I couldn't find a matching result in relationship_table.csv.\n\n" + _help_text()

    # ── "Most affect / top categories" intent ────────────────────────────────
    if _is_top_impact_intent(q):
        ranked = _rank_most_affecting(df, k=5)

        title_bits = []
        if indep:
            title_bits.append(_humanize_indep(indep))
        if group_type:
            title_bits.append(group_type.replace("_", " "))
        if horizon:
            title_bits.append(horizon.replace("_", " "))

        title = " / ".join(title_bits) if title_bits else "results"

        lines = [f"**Top groups/categories that affect RSUI most ({title}):**"]
        for _, r in ranked.iterrows():
            row = r.to_dict()
            lines.append(f"\n**{row.get('group_label','')}**\n{naturalize_row(row, show_stats=show_stats)}")
        return "\n".join(lines)

    # ── Compare intent (rank by significance then effect size) ───────────────
    if _is_compare_intent(q):
        ranked = _rank_most_affecting(df, k=5)
        lines = ["**Comparison (ranked by confidence then effect size):**"]
        for _, r in ranked.iterrows():
            row = r.to_dict()
            lines.append(f"\n**{row.get('group_label','')}**\n{naturalize_row(row, show_stats=show_stats)}")
        return "\n".join(lines)

    # ── Single best row ──────────────────────────────────────────────────────
    out = df.copy()
    out["p_rank"] = out["pvalue"].fillna(999999)
    out["abs_effect"] = out["effect_value"].abs()
    out = out.sort_values(["p_rank", "abs_effect"], ascending=[True, False], na_position="last")

    best = out.iloc[0].to_dict()
    return naturalize_row(best, show_stats=show_stats)