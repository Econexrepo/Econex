from __future__ import annotations

import os
import pathlib
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

import pandas as pd

# Groq via OpenAI-compatible client (same approach as your friend's file)
from openai import OpenAI


# =============================================================================
# Groq client setup
# =============================================================================
_GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
_GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.2"))

_GROQ_CLIENT: Optional[OpenAI] = None
if _GROQ_API_KEY:
    _GROQ_CLIENT = OpenAI(
        api_key=_GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

_GROQ_CLIENT: Optional[OpenAI] = None
if _GROQ_API_KEY:
    _GROQ_CLIENT = OpenAI(
        api_key=_GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

def _groq_chat(messages: List[Dict[str, str]]) -> str:
    if _GROQ_CLIENT is None:
        return (
            "Groq is not configured (missing GROQ_API_KEY). "
            "Set GROQ_API_KEY in your environment (or .env) to enable LLM responses."
        )

    resp = _GROQ_CLIENT.chat.completions.create(
        model=_GROQ_MODEL,
        messages=messages,
        temperature=_GROQ_TEMPERATURE,
    )
    return (resp.choices[0].message.content or "").strip()


# =============================================================================
# Load relationship_table.csv (your robust search)
# =============================================================================
def _find_relationship_table() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for parent in [here.parent] + list(here.parents)[:8]:
        p = parent / "relationship_table.csv"
        if p.exists():
            return p
    p = pathlib.Path.cwd() / "relationship_table.csv"
    if p.exists():
        return p
    raise FileNotFoundError("relationship_table.csv not found (searched parents and CWD).")


def _load_relationship_table() -> pd.DataFrame:
    path = _find_relationship_table()
    df = pd.read_csv(path)

    required = {
        "dep_var", "indep_var", "group_type", "group_label",
        "horizon", "effect_value", "pvalue", "aic", "bic", "n_obs", "description"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"relationship_table.csv missing columns: {sorted(missing)}")

    for c in ["dep_var", "indep_var", "group_type", "group_label", "horizon", "description", "source_file", "status"]:
        if c in df.columns:
            df[c] = df[c].astype(str).fillna("")

    for c in ["effect_value", "pvalue", "aic", "bic", "n_obs"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["_dep_l"] = df["dep_var"].str.strip().str.lower()
    df["_indep_l"] = df["indep_var"].str.strip().str.lower()
    df["_gtype_l"] = df["group_type"].str.strip().str.lower()
    df["_glabel_l"] = df["group_label"].str.strip().str.lower()
    df["_horizon_l"] = df["horizon"].str.strip().str.lower()

    print(f"[ai_service] Loaded relationship_table.csv from {path} ({len(df)} rows)")
    return df


_REL = _load_relationship_table()

INDEP_VOCAB: List[str] = sorted(set(_REL["_indep_l"].dropna()))
GTYPE_VOCAB: List[str] = sorted(set(_REL["_gtype_l"].dropna()))
GLABEL_VOCAB: List[str] = sorted(set(_REL["_glabel_l"].dropna()), key=len, reverse=True)


# =============================================================================
# Text helpers (your logic)
# =============================================================================
def _norm(s: str) -> str:
    s = str(s or "").lower().strip()
    s = s.replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


DETAILS_ONLY_SET = {"show details", "details", "show stats", "stats", "numbers", "show numbers"}


def _is_details_only(q: str) -> bool:
    return _norm(q) in DETAILS_ONLY_SET


DETAILS_ONLY_SET = {"show details", "details", "show stats", "stats", "numbers", "show numbers"}


def _is_details_only(q: str) -> bool:
    return _norm(q) in DETAILS_ONLY_SET


def _wants_details(q: str) -> bool:
    qn = _norm(q)
    return any(k in qn for k in [
        "show details", "details", "numbers", "stats", "statistics",
        "p value", "p-value", "pvalue", "coef", "coefficient", "aic", "bic"
    ])


def _extract_horizon(q: str) -> Optional[str]:
    qn = _norm(q)
    if any(k in qn for k in ["long run", "long-run", "longrun", "lr"]):
        return "long_run"
    if any(k in qn for k in ["short run", "short-run", "shortrun", "sr"]):
        return "short_run"
    return None


def _default_horizon_if_relationship(q: str) -> Optional[str]:
    qn = _norm(q)
    if _extract_horizon(qn):
        return None
    if any(k in qn for k in ["relationship", "relation", "association", "link", "impact", "effect", "influence"]):
        return "long_run"
    return None


def _extract_indep(q: str) -> Optional[str]:
    qn = _norm(q)

    if any(k in qn for k in [
        "government expenditure", "public expenditure", "government spending", "public spending",
        "gov expenditure", "gov exp", "govt expenditure", "expanditure"
    ]):
        if any(k in qn for k in [
            "capital", "recurrent", "type", "types",
            "group", "groups",
            "category", "categories"
        ]):
            return "government_expenditure"
        return "total_expenditure"

    if "expenditure" in qn or "spending" in qn:
        if any(k in qn for k in ["capital", "recurrent", "type"]):
            return "government_expenditure"
        return "total_expenditure"

    synonyms = {
        "unemployment": ["unemployment", "jobless", "joblessness", "unemployed"],
        "gdp": ["gdp", "gross domestic"],
        "pce": ["pce", "consumption", "consumption expenditure", "personal consumption"],
        "wage": ["wage", "wages", "salary", "salaries", "earnings", "income", "pay"],
        "total_expenditure": ["total expenditure", "overall expenditure", "total spending"],
    }

    for indep, keys in synonyms.items():
        if any(k in qn for k in keys):
            return indep

    for v in INDEP_VOCAB:
        if v and (v in qn or v.replace("_", " ") in qn):
            return v

    return None


def _is_compare_intent(q: str) -> bool:
    qn = _norm(q)
    return any(w in qn for w in [
        "compare", "comparison", "rank", "ranking",
        "top", "best", "worst", "highest", "lowest",
        "strongest", "largest", "smallest", "vs", "versus"
    ])


def _is_top_impact_intent(q: str) -> bool:
    qn = _norm(q)
    return any(w in qn for w in [
        "mostly affect", "affect the most", "affects the most",
        "most impact", "highest impact", "strongest impact",
        "biggest impact", "which category", "which categories",
        "which age group", "which age groups",
        "which education", "which education levels",
        "top categories", "top groups", "rank categories", "rank groups",
        "strongest effect", "largest effect"
    ])


def _is_list_groups_intent(q: str) -> bool:
    qn = _norm(q)
    return any(w in qn for w in [
        "list groups", "list group", "list group labels", "list labels",
        "show groups", "show group labels", "show labels",
        "all groups", "all categories", "all group labels",
        "what groups", "what categories", "which groups are there",
        "group labels", "available groups", "available categories",
        "list categories"
    ])


def _extract_group_type(q: str, indep: Optional[str]) -> Optional[str]:
    qn = _norm(q)

    if indep == "wage" and any(k in qn for k in ["compare", "comparison", "rank", "top", "affect the most", "most impact"]):
        return "category_name"

    if "age" in qn:
        return "age_group"
    if "education" in qn or re.search(r"(?<!\w)edu(?!\w)", qn):
        return "edu"
    if any(k in qn for k in ["capital", "recurrent", "expenditure type", "exp type", "type"]):
        return "exp_type"
    if "sector" in qn:
        return "sector_name"
    if any(k in qn for k in ["category", "categories", "by category"]):
        if indep == "wage":
            return "category_name"
        return "category"

    for gt in GTYPE_VOCAB:
        if gt and (gt in qn or gt.replace("_", " ") in qn):
            return gt
    return None


def _auto_group_type_for_indep(indep: str) -> Optional[str]:
    if not indep:
        return None
    sub = _REL[_REL["_indep_l"] == indep.lower()]
    if sub.empty:
        return None
    return str(sub["_gtype_l"].value_counts().idxmax())


def _extract_group_label_exact(q: str) -> Optional[str]:
    qn = _norm(q)
    for lbl in GLABEL_VOCAB:
        if not lbl:
            continue
        if re.search(r"(?<!\w)" + re.escape(lbl) + r"(?!\w)", qn):
            return lbl
        if lbl.replace("_", " ") in qn:
            return lbl
    return None


def _is_greeting(q: str) -> bool:
    qn = _norm(q)
    greetings = {
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "thank you", "thanks", "ok", "okay", "bye"
    }
    return qn in greetings


# =============================================================================
# FAQ / General knowledge base
# =============================================================================
GENERAL_FAQ = {
    "what is rsui":
        "RSUI stands for the Reported Social Unrest Index. It is used to measure the level of reported social unrest such as protests, riots, strikes, and demonstrations.",

    "what does rsui mean":
        "RSUI stands for the Reported Social Unrest Index. It is used to measure the level of reported social unrest such as protests, riots, strikes, and demonstrations.",

    "how have you got the results":
        "The results were obtained by training ARDL econometric models using data collected from multiple official sources and then storing the estimated relationships in the analysis output.",

    "how did you get the results":
        "The results were obtained by training ARDL econometric models using data collected from multiple official sources and then storing the estimated relationships in the analysis output.",

    "how were the results obtained":
        "The results were obtained using ARDL econometric models that estimate the relationship between RSUI and economic indicators in both the short run and long run.",

    "what model is used":
        "The analysis uses the ARDL model, which stands for AutoRegressive Distributed Lag. It is used to study both short-run and long-run relationships between variables.",

    "which model is used":
        "The analysis uses the ARDL model, which stands for AutoRegressive Distributed Lag. It is used to study both short-run and long-run relationships between variables.",

    "what is ardl":
        "ARDL stands for AutoRegressive Distributed Lag. It is an econometric model used to estimate both short-run and long-run relationships between variables.",

    "sources of the data":
        "The data used in this research come from official sources such as the Central Bank of Sri Lanka (CBSL), the Department of Census and Statistics, and annual reports.",

    "what are the data sources":
        "The data sources include the Central Bank of Sri Lanka (CBSL), the Department of Census and Statistics, and annual reports.",

    "what data sources are used":
        "The data sources include the Central Bank of Sri Lanka (CBSL), the Department of Census and Statistics, and annual reports.",

    "available categories of unemployment by age":
        "You can ask the chatbot to list the unemployment age categories in the analysis. For example: 'list unemployment age groups' or 'show unemployment age groups'.",

    "compare categories of unemployment by age":
        "You can compare unemployment age categories by asking: 'compare unemployment age groups' or 'which unemployment age group affects RSUI the most?'.",

    "compare agri production":
        "You can compare agricultural production categories by asking: 'compare agri production categories' or 'which agri production category affects RSUI the most?'.",

    "what variables are analysed":
        "The analysis focuses on RSUI against variables such as unemployment, government expenditure, GDP, wages, personal consumption expenditure, and agricultural production depending on the available model outputs.",

    "what variables are analyzed":
        "The analysis focuses on RSUI against variables such as unemployment, government expenditure, GDP, wages, personal consumption expenditure, and agricultural production depending on the available model outputs.",

    "what is the purpose of this chatbot":
        "This chatbot is designed to explain the econometric results and answer general questions related to the research project.",

    "what does a p value mean":
        "A p-value shows the statistical significance of a result. In this project, a p-value below 0.05 is usually treated as statistically significant.",

    "what is a p value":
        "A p-value shows the statistical significance of a result. In this project, a p-value below 0.05 is usually treated as statistically significant.",
}


def _check_general_faq(question: str) -> Optional[str]:
    q = _norm(question)
    for k, v in GENERAL_FAQ.items():
        if k in q:
            return v
    return None


# =============================================================================
# Filtering / ranking (your logic)
# =============================================================================
def _filter(
    dep: str = "rsui",
    indep: Optional[str] = None,
    horizon: Optional[str] = None,
    group_type: Optional[str] = None,
    group_label_exact: Optional[str] = None,
    group_hint: Optional[str] = None,
) -> pd.DataFrame:
    df = _REL[_REL["_dep_l"] == dep.lower()].copy()

    if indep:
        df = df[df["_indep_l"] == indep.lower()]
    if horizon:
        df = df[df["_horizon_l"] == horizon.lower()]
    if group_type:
        df = df[df["_gtype_l"] == group_type.lower()]

    if group_label_exact:
        df = df[df["_glabel_l"] == _norm(group_label_exact)]
    elif group_hint:
        gh = _norm(group_hint)
        df = df[df["_glabel_l"].apply(lambda x: gh in _norm(x))]

    return df


def _rank_rows(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["p_rank"] = out["pvalue"].fillna(999999)
    out["abs_effect"] = out["effect_value"].abs()
    return out.sort_values(["p_rank", "abs_effect"], ascending=[True, False], na_position="last")


def _rank_most_affecting(df: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    out = df.copy()
    out["abs_effect"] = out["effect_value"].abs()
    out["sig_flag"] = out["pvalue"].apply(lambda p: 1 if pd.notna(p) and p < 0.05 else 0)
    out = out.sort_values(["sig_flag", "abs_effect"], ascending=[False, False], na_position="last")
    return out.head(k)


def _best_row_per_group_label(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    ranked = _rank_rows(df)
    return ranked.groupby("group_label", dropna=False, sort=False).head(1)


def _is_overall_row(row: pd.Series) -> bool:
    gt = str(row.get("group_type", "")).strip().lower()
    gl = str(row.get("group_label", "")).strip().lower()
    return gt == "tot_category" or gl.startswith("total")


def _pick_overall_row(df: pd.DataFrame) -> Optional[dict]:
    if df.empty:
        return None
    overall = df[df.apply(_is_overall_row, axis=1)]
    if overall.empty:
        return None
    return _rank_rows(overall).iloc[0].to_dict()


def _prefer_long_run_if_available(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    long_df = df[df["_horizon_l"] == "long_run"]
    return long_df if not long_df.empty else df


# =============================================================================
# Session memory (your logic)
# =============================================================================
@dataclass
class RetrievalState:
    last_indep: Optional[str] = None
    last_horizon: Optional[str] = None
    last_group_type: Optional[str] = None
    last_group_label_exact: Optional[str] = None
    last_group_hint: Optional[str] = None
    last_rows: List[Dict[str, Any]] = field(default_factory=list)
    last_presented_rows: List[Dict[str, Any]] = field(default_factory=list)
    last_nonvague_user_msg: str = ""


_SESSION_MEM: dict[str, RetrievalState] = {}

_VAGUE_PATTERNS = [
    r"^\s*(give\s+details|details|show\s+details|show\s+stats|stats|numbers)\s*$",
    r"^\s*(explain\s+more|more\s+info|tell\s+me\s+more|explain)\s*$",

    r"^\s*(why\??)\s*$",
    r"^\s*(how\??)\s*$",

    r"^\s*(what\s+is\s+this)\s*$",
    r"^\s*(what\s+is\s+this\s+value)\s*$",
    r"^\s*(what\s+does\s+this\s+mean)\s*$",
    r"^\s*(this\s+value)\s*$",
    r"^\s*(this\s+result)\s*$",
    r"^\s*(that\s+value)\s*$",
    r"^\s*(that\s+result)\s*$",

    r"^\s*(compare\s+them|compare\s+those|compare)\s*$",
    r"^\s*(what\s+about\s+short\s*run\??|short\s*run\??)\s*$",
    r"^\s*(what\s+about\s+long\s*run\??|long\s*run\??)\s*$",
    r"^\s*(and\s+short\s*run\??|and\s+long\s*run\??)\s*$",
    r"^\s*(continue|go\s+on|next)\s*$",
]


def _is_vague_followup(message: str) -> bool:
    q = _norm(message)
    if len(q) <= 2:
        return True
    return any(re.match(p, q) for p in _VAGUE_PATTERNS)


def _extract_last_meaningful_user_text(history: Optional[List[Dict[str, str]]], lookback: int = 12) -> Optional[str]:
    if not history:
        return None
    for item in reversed(history[-lookback:]):
        if item.get("role") != "user":
            continue
        text = item.get("content") or ""
        if text and not _is_vague_followup(text):
            return text
    return None


def _merge_context(message: str, history: Optional[List[Dict[str, str]]], state: RetrievalState) -> Tuple[str, bool]:
    vague = _is_vague_followup(message)
    if not vague:
        return message, False
    base = state.last_nonvague_user_msg or _extract_last_meaningful_user_text(history) or ""
    if not base:
        return message, True
    return f"{base} {message}", True


def retrieve_relevant_rows(
    message: str,
    history: Optional[List[Dict[str, str]]],
    session_id: str,
    *,
    limit_rows: int = 8,
    reuse_last_rows_for_details: bool = True,
) -> Optional[List[Dict[str, Any]]]:
    state = _SESSION_MEM.setdefault(session_id, RetrievalState())

    effective_query, vague = _merge_context(message, history, state)

    indep = _extract_indep(effective_query)
    horizon = _extract_horizon(effective_query) or _default_horizon_if_relationship(effective_query)
    group_type = _extract_group_type(effective_query, indep)

    if indep and not group_type:
        group_type = _auto_group_type_for_indep(indep)

    group_label_exact = _extract_group_label_exact(effective_query)

    wants_details = _wants_details(message)
    horizon_override = _extract_horizon(message)
    if vague and reuse_last_rows_for_details and state.last_rows and wants_details and not horizon_override:
        return state.last_rows

    group_hint = None
    if not group_label_exact:
        qn = _norm(effective_query)
        cleaned = re.sub(
            r"(rsui|relationship|relation|association|link|impact|effect|influence|between|with|versus|vs|compare|rank|top|best|worst|highest|lowest|strongest|details|stats|statistics|list|groups|group\s*labels|labels)",
            " ",
            qn,
        )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) >= 2:
            group_hint = cleaned

    if vague:
        indep = indep or state.last_indep
        horizon = horizon or state.last_horizon
        group_type = group_type or state.last_group_type
        group_label_exact = group_label_exact or state.last_group_label_exact
        group_hint = group_hint or state.last_group_hint

    if horizon_override:
        horizon = horizon_override

    df = _filter(
        dep="rsui",
        indep=indep,
        horizon=horizon,
        group_type=group_type,
        group_label_exact=group_label_exact,
        group_hint=group_hint,
    )

    if df.empty and group_label_exact:
        df = _filter(dep="rsui", indep=indep, horizon=horizon, group_type=group_type, group_label_exact=None, group_hint=group_hint)
    if df.empty and group_hint:
        df = _filter(dep="rsui", indep=indep, horizon=horizon, group_type=group_type, group_label_exact=group_label_exact, group_hint=None)
    if df.empty and group_type:
        df = _filter(dep="rsui", indep=indep, horizon=None, group_type=None, group_label_exact=group_label_exact, group_hint=group_hint)
    if df.empty and horizon:
        df = _filter(dep="rsui", indep=indep, horizon=None, group_type=group_type, group_label_exact=group_label_exact, group_hint=group_hint)

    if df.empty:
        return None

    rows = _rank_rows(df).head(limit_rows).to_dict(orient="records")

    state.last_indep = indep
    state.last_horizon = horizon
    state.last_group_type = group_type
    state.last_group_label_exact = group_label_exact
    state.last_group_hint = group_hint
    state.last_rows = rows
    if not vague:
        state.last_nonvague_user_msg = message

    return rows


# =============================================================================
# Groq grounding prompt + formatting
# =============================================================================
def _rows_context_json(rows: List[Dict[str, Any]], max_rows: int = 10) -> str:
    df = pd.DataFrame(rows).head(max_rows)
    cols = [
        "dep_var", "indep_var", "group_type", "group_label", "horizon",
        "effect_value", "pvalue", "aic", "bic", "n_obs", "status", "source_file", "description",
    ]
    cols = [c for c in cols if c in df.columns]
    return df[cols].to_json(orient="records", indent=2)


def _make_system_prompt(show_stats: bool, has_analysis_rows: bool) -> str:
    stats_rule = (
        "- Include key numbers (effect_value, pvalue, and n_obs if present).\n"
        if show_stats else
        "- Do not dump lots of numbers; summarize direction and significance briefly. End with: '(Say show details for numbers.)'.\n"
    )

    if has_analysis_rows:
        source_rule = (
            "- The provided rows are from our analysis. Base your answer only on those rows.\n"
            "- Do not say 'relationship table' or 'database'.\n"
            "- Use natural phrases like 'According to our analysis', 'Based on our analysis', or 'The analysis suggests'.\n"
        )
    else:
        source_rule = (
            "- No analysis rows are provided for this question.\n"
            "- Answer naturally using general knowledge.\n"
            "- Do not mention missing tables, files, or internal retrieval steps.\n"
        )

    return (
        "You are Econex, a decision-friendly data assistant.\n"
        "Handle greetings such as hi, hello, hey, thanks, and bye naturally and briefly.\n"
        "Be friendly for greetings, but concise.\n"
        f"{source_rule}"
        "Rules:\n"
        "- Do not invent coefficients, p-values, categories, or data.\n"
        "- Direction comes from effect_value sign: >0 increases RSUI, <0 decreases RSUI.\n"
        "- Confidence from pvalue: <0.01 high, <0.05 moderate, else low.\n"
        "- Mention statistical significance only if pvalue is available.\n"
        "- If pvalue is missing, do NOT mention significance.\n"
        f"{stats_rule}"
        "- If the analysis rows include a total or overall row for total unemployment or total expenditure, prefer that row instead of subgroup rows.\n"
        "- Keep the answer concise, clear, and presentation-friendly.\n"
    )


# =============================================================================
# Main API: get_ai_response
# =============================================================================
def get_ai_response(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    session_id: Optional[str] = None,
) -> str:
    q = message or ""
    session_id = session_id or "default-session"
    state = _SESSION_MEM.setdefault(session_id, RetrievalState())

    # 1) FAQ first
    faq_answer = _check_general_faq(q)
    if faq_answer:
        return faq_answer

    # 2) direct details for last shown results
    if _is_details_only(q):
        if state.last_presented_rows:
            # return deterministic details without Groq (fast + precise)
            lines = ["**Details for the last shown result(s):**"]
            for r in state.last_presented_rows[:12]:
                lines.append(pd.Series(r).to_string())
                lines.append("")
            return "\n".join(lines).strip()
        return "Nothing to show details for yet. Ask a question first."

    # 3) greetings through LLM/general response
    if _is_greeting(q):
        if _GROQ_CLIENT is None:
            qn = _norm(q)
            if qn in {"thank you", "thanks"}:
                return "You're welcome."
            if qn == "bye":
                return "Goodbye."
            return "Hello."
        try:
            return _groq_chat([
                {"role": "system", "content": _make_system_prompt(show_stats=False, has_analysis_rows=False)},
                {"role": "user", "content": q}
            ])
        except Exception:
            qn = _norm(q)
            if qn in {"thank you", "thanks"}:
                return "You're welcome."
            if qn == "bye":
                return "Goodbye."
            return "Hello."

    big_intent = _is_compare_intent(q) or _is_top_impact_intent(q) or _is_list_groups_intent(q)
    limit = 150 if big_intent else 12

    # 4) Try analysis rows
    rows = retrieve_relevant_rows(
        message=q,
        history=history,
        session_id=session_id,
        limit_rows=limit,
        reuse_last_rows_for_details=True,
    )

    # 5) If no matching analysis result, answer generally
    if not rows:
        if _GROQ_CLIENT is None:
            return "I couldn't find a matching analysis result, and Groq is not configured for a general response."

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _make_system_prompt(show_stats=False, has_analysis_rows=False)}
        ]

        if history:
            for m in history[-8:]:
                role = (m.get("role") or "").strip().lower()
                content = m.get("content")
                if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                    messages.append({"role": role, "content": content.strip()})

        messages.append({
            "role": "user",
            "content": f"User question: {message}"
        })

        try:
            return _groq_chat(messages)
        except Exception as e:
            return f"General response failed: {type(e).__name__}: {e}"

    df = pd.DataFrame(rows)
    show_stats = _wants_details(q)

    # prefer long run for broad intents unless user forced horizon
    if big_intent and _extract_horizon(q) is None:
        df = _prefer_long_run_if_available(df)

    # Decide what to PRESENT (distinct group labels for compare/top/list)
    presented_rows: List[Dict[str, Any]] = []

    if _is_list_groups_intent(q):
        non_total = df[~df.apply(_is_overall_row, axis=1)].copy()
        if _extract_horizon(q) is None:
            non_total = _prefer_long_run_if_available(non_total)
        presented_df = _rank_rows(_best_row_per_group_label(non_total)).head(15)
        presented_rows = presented_df.to_dict(orient="records")

    elif _is_top_impact_intent(q) or _is_compare_intent(q):
        non_total = df[~df.apply(_is_overall_row, axis=1)].copy()
        if non_total.empty:
            non_total = df.copy()
        distinct = _best_row_per_group_label(non_total)
        ranked = _rank_most_affecting(distinct, k=min(20, len(distinct)))
        presented_rows = ranked.to_dict(orient="records")

    else:
        overall = _pick_overall_row(df)
        if overall:
            presented_rows = [overall]
        else:
            best = _rank_rows(df).iloc[0].to_dict()
            presented_rows = [best]

    # store what we showed (enables "show details")
    state.last_presented_rows = presented_rows

    # If Groq isn't configured, fallback to deterministic dump (but still works)
    if _GROQ_CLIENT is None:
        return (
            "Groq is not configured (missing GROQ_API_KEY). "
            "Set GROQ_API_KEY to enable LLM responses.\n\n"
            + _rows_context_json(presented_rows, max_rows=10)
        )

    # Groq: generate natural language grounded in presented_rows
    context_json = _rows_context_json(presented_rows, max_rows=10)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _make_system_prompt(show_stats, has_analysis_rows=True)}
    ]

    # small history slice for continuity
    if history:
        for m in history[-8:]:
            role = (m.get("role") or "").strip().lower()
            content = m.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content.strip()})

    messages.append({
        "role": "user",
        "content": (
            f"User question: {message}\n\n"
            f"Analysis rows (JSON):\n{context_json}\n"
        )
    })

    try:
        return _groq_chat(messages)
    except Exception as e:
        return (
            f"Groq request failed: {type(e).__name__}: {e}\n\n"
            "Fallback rows:\n" + context_json
        )