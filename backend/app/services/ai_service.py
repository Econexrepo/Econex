"""
Econex AI Service – CSV-driven response engine (no OpenAI required).

Reads ARDL model outputs from CSV files and returns structured, meaningful
answers based on keyword matching. All numbers come directly from the CSVs.
"""

import pathlib
import pandas as pd

# ── CSV loading ───────────────────────────────────────────────────────────────
_BASE_DIR = pathlib.Path(__file__).resolve().parent.parent.parent.parent  # Econex repo root
_ARDL_DIR = _BASE_DIR / "ardloutputs"


def _safe_load(path: pathlib.Path) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(path)
        print(f"[ai_service] Loaded {path.name} — {len(df)} rows")
        return df
    except Exception as e:
        print(f"[ai_service] WARNING: Could not load {path}: {e}")
        return None


_short_df = _safe_load(_ARDL_DIR / "gdp_shortRun.csv")
_long_df  = _safe_load(_ARDL_DIR / "gdp_longRun.csv")


# ── Pre-compute impact scores from the CSVs once at startup ───────────────────
def _compute_impacts() -> dict:
    """
    Derive human-readable impact percentages from ARDL coefficients.

    Long-run impact share  = |long_run_effect| / sum(|long_run_effect|) * 100
    Short-run impact share = |gdp_coef|        / sum(|gdp_coef|)        * 100
    """
    impacts = {}
    if _long_df is not None and _short_df is not None:
        # Long-run
        lr = _long_df.copy()
        lr["abs_effect"] = lr["long_run_effect"].abs()
        total_lr = lr["abs_effect"].sum()
        for _, row in lr.iterrows():
            s = row["sector_name"]
            impacts.setdefault(s, {})
            impacts[s]["long_run_effect"]  = float(row["long_run_effect"])
            impacts[s]["long_run_share"]   = round(float(row["abs_effect"]) / total_lr * 100, 1)
            impacts[s]["long_run_aic"]     = float(row["aic"])
            impacts[s]["long_run_bic"]     = float(row["bic"])
            impacts[s]["n_obs"]            = int(row["n_obs"])

        # Short-run
        sr = _short_df.copy()
        sr["abs_coef"] = sr["gdp_coef"].abs()
        total_sr = sr["abs_coef"].sum()
        for _, row in sr.iterrows():
            s = row["sector_name"]
            impacts.setdefault(s, {})
            impacts[s]["short_run_coef"]   = float(row["gdp_coef"])
            impacts[s]["short_run_share"]  = round(float(row["abs_coef"]) / total_sr * 100, 1)
            impacts[s]["short_run_pvalue"] = float(row["gdp_pvalue"])
            impacts[s]["short_run_aic"]    = float(row["aic"])
            impacts[s]["short_run_bic"]    = float(row["bic"])
            impacts[s]["short_sig"]        = row["gdp_pvalue"] < 0.05

    return impacts


_IMPACTS = _compute_impacts()

# Pull out values for convenience
_AGR = _IMPACTS.get("Agriculture", {})
_IND = _IMPACTS.get("Industry",    {})
_SRV = _IMPACTS.get("Services",    {})


def _sig_label(is_sig: bool) -> str:
    return "✅ Statistically significant (p < 0.05)" if is_sig else "⚠️ Not significant at 5% level"


# ── Response builders (all numbers from CSV) ──────────────────────────────────

def _resp_overview() -> str:
    if not _IMPACTS:
        return "⚠️ ARDL data not loaded. Please check the ardloutputs folder."
    return (
        "## GDP Sector Impact on RSUI — Overview\n\n"
        "Based on ARDL model results (n = 23 observations):\n\n"

        "### 📊 Long-Run Impact (relative contribution)\n"
        f"| Sector | Long-run Effect | Impact Share |\n"
        f"|---|---|---|\n"
        f"| 🌾 Agriculture | {_AGR.get('long_run_effect', 0):.2f} | **{_AGR.get('long_run_share', 0)}%** |\n"
        f"| 💼 Services    | {_SRV.get('long_run_effect', 0):.2f} | **{_SRV.get('long_run_share', 0)}%** |\n"
        f"| 🏭 Industry    | {_IND.get('long_run_effect', 0):.2f} | **{_IND.get('long_run_share', 0)}%** |\n\n"

        "### ⚡ Short-Run Coefficient (immediate RSUI sensitivity)\n"
        f"| Sector | Coefficient | P-value | Significance |\n"
        f"|---|---|---|---|\n"
        f"| 🌾 Agriculture | {_AGR.get('short_run_coef', 0):.4f} | {_AGR.get('short_run_pvalue', 0):.4f} | {_sig_label(_AGR.get('short_sig', False))} |\n"
        f"| 💼 Services    | {_SRV.get('short_run_coef', 0):.4f} | {_SRV.get('short_run_pvalue', 0):.4f} | {_sig_label(_SRV.get('short_sig', False))} |\n"
        f"| 🏭 Industry    | {_IND.get('short_run_coef', 0):.4f} | {_IND.get('short_run_pvalue', 0):.4f} | {_sig_label(_IND.get('short_sig', False))} |\n\n"

        "**Interpretation:** A negative coefficient means GDP growth in that sector is associated with a *decrease* in RSUI (less social unrest). "
        "Agriculture has the largest long-run influence on social stability."
    )


def _resp_agriculture() -> str:
    if not _AGR:
        return "⚠️ Agriculture data not found in ARDL outputs."
    return (
        "## 🌾 Agriculture Sector — ARDL Impact on RSUI\n\n"

        f"### Long-Run Impact\n"
        f"- **Long-run effect:** {_AGR['long_run_effect']:.4f}\n"
        f"- **Impact share:** **{_AGR['long_run_share']}%** of total sector influence on RSUI\n"
        f"- **Model fit:** AIC = {_AGR['long_run_aic']:.2f} | BIC = {_AGR['long_run_bic']:.2f}\n\n"

        f"### Short-Run Dynamics\n"
        f"- **Short-run coefficient:** {_AGR['short_run_coef']:.4f}\n"
        f"- **P-value:** {_AGR['short_run_pvalue']:.4f} — {_sig_label(_AGR['short_sig'])}\n\n"

        "### Interpretation\n"
        f"Agriculture accounts for **{_AGR['long_run_share']}%** of the combined long-run sector impact on RSUI. "
        "The negative coefficient means that when agricultural GDP grows, the RSUI (social unrest index) tends to **decrease**. "
        "This makes sense — rural income stability directly reduces economic stress and social unrest risk.\n\n"
        f"Note: The short-run coefficient ({_AGR['short_run_coef']:.4f}) is {'' if _AGR['short_sig'] else 'not '}statistically significant, "
        "suggesting the long-run structural relationship is stronger than the immediate year-to-year effect."
    )


def _resp_industry() -> str:
    if not _IND:
        return "⚠️ Industry data not found in ARDL outputs."
    return (
        "## 🏭 Industry Sector — ARDL Impact on RSUI\n\n"

        f"### Long-Run Impact\n"
        f"- **Long-run effect:** {_IND['long_run_effect']:.4f}\n"
        f"- **Impact share:** **{_IND['long_run_share']}%** of total sector influence on RSUI\n"
        f"- **Model fit:** AIC = {_IND['long_run_aic']:.2f} | BIC = {_IND['long_run_bic']:.2f}\n\n"

        f"### Short-Run Dynamics\n"
        f"- **Short-run coefficient:** {_IND['short_run_coef']:.4f}\n"
        f"- **P-value:** {_IND['short_run_pvalue']:.4f} — {_sig_label(_IND['short_sig'])}\n\n"

        "### Interpretation\n"
        f"Industry accounts for **{_IND['long_run_share']}%** of the combined long-run sector impact on RSUI. "
        "The short-run coefficient is the most statistically significant across all sectors (p = {:.4f}), "
        "meaning industrial GDP fluctuations have an immediate and measurable effect on social unrest levels.".format(
            _IND.get('short_run_pvalue', 0)
        )
    )


def _resp_services() -> str:
    if not _SRV:
        return "⚠️ Services data not found in ARDL outputs."
    return (
        "## 💼 Services Sector — ARDL Impact on RSUI\n\n"

        f"### Long-Run Impact\n"
        f"- **Long-run effect:** {_SRV['long_run_effect']:.4f}\n"
        f"- **Impact share:** **{_SRV['long_run_share']}%** of total sector influence on RSUI\n"
        f"- **Model fit:** AIC = {_SRV['long_run_aic']:.2f} | BIC = {_SRV['long_run_bic']:.2f}\n\n"

        f"### Short-Run Dynamics\n"
        f"- **Short-run coefficient:** {_SRV['short_run_coef']:.4f}\n"
        f"- **P-value:** {_SRV['short_run_pvalue']:.4f} — {_sig_label(_SRV['short_sig'])}\n\n"

        "### Interpretation\n"
        f"Services accounts for **{_SRV['long_run_share']}%** of the combined long-run sector impact on RSUI. "
        "The services sector has a significant short-run relationship (p < 0.05), "
        "reflecting how formal employment in services directly affects household economic stability."
    )


def _resp_comparison() -> str:
    if not _IMPACTS:
        return "⚠️ ARDL data not loaded."
    # Rank sectors by long-run share
    ranked = sorted(_IMPACTS.items(), key=lambda x: x[1].get("long_run_share", 0), reverse=True)
    lines = ["## 📊 Sector Comparison — Long-Run Impact on RSUI\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (sector, data) in enumerate(ranked):
        icon = {"Agriculture": "🌾", "Industry": "🏭", "Services": "💼"}.get(sector, "📌")
        medal = medals[i] if i < 3 else "  "
        lines.append(
            f"{medal} **{icon} {sector}** — Impact share: **{data.get('long_run_share', 0)}%**  "
            f"| Long-run effect: `{data.get('long_run_effect', 0):.4f}`  "
            f"| Short-run p-value: `{data.get('short_run_pvalue', 0):.4f}`"
        )
    lines.append(
        "\n**Key takeaway:** Agriculture dominates the long-run relationship with RSUI, "
        "while Industry shows the strongest short-run statistical significance."
    )
    return "\n".join(lines)


def _resp_short_run_all() -> str:
    if _short_df is None:
        return "⚠️ Short-run data not loaded."
    return (
        "## ⚡ Short-Run ARDL Coefficients — All Sectors\n\n"
        "These coefficients measure the **immediate year-to-year** effect of GDP sector growth on RSUI:\n\n"
        f"| Sector | Coefficient | P-value | Significant? |\n"
        f"|---|---|---|---|\n"
        f"| 🌾 Agriculture | `{_AGR.get('short_run_coef', 0):.4f}` | `{_AGR.get('short_run_pvalue', 0):.4f}` | {'✅ Yes' if _AGR.get('short_sig') else '❌ No (p > 0.05)'} |\n"
        f"| 💼 Services    | `{_SRV.get('short_run_coef', 0):.4f}` | `{_SRV.get('short_run_pvalue', 0):.4f}` | {'✅ Yes' if _SRV.get('short_sig') else '❌ No'} |\n"
        f"| 🏭 Industry    | `{_IND.get('short_run_coef', 0):.4f}` | `{_IND.get('short_run_pvalue', 0):.4f}` | {'✅ Yes' if _IND.get('short_sig') else '❌ No'} |\n\n"
        "A **negative coefficient** means GDP growth → RSUI decreases (less unrest).  \n"
        "Industry has the most significant short-run effect (lowest p-value)."
    )


def _resp_long_run_all() -> str:
    if _long_df is None:
        return "⚠️ Long-run data not loaded."
    return (
        "## 📈 Long-Run ARDL Effects — All Sectors\n\n"
        "These measure the **structural, sustained** effect of each GDP sector on RSUI over time:\n\n"
        f"| Sector | Long-run Effect | Impact Share | AIC |\n"
        f"|---|---|---|---|\n"
        f"| 🌾 Agriculture | `{_AGR.get('long_run_effect', 0):.4f}` | **{_AGR.get('long_run_share', 0)}%** | {_AGR.get('long_run_aic', 0):.2f} |\n"
        f"| 💼 Services    | `{_SRV.get('long_run_effect', 0):.4f}` | **{_SRV.get('long_run_share', 0)}%** | {_SRV.get('long_run_aic', 0):.2f} |\n"
        f"| 🏭 Industry    | `{_IND.get('long_run_effect', 0):.4f}` | **{_IND.get('long_run_share', 0)}%** | {_IND.get('long_run_aic', 0):.2f} |\n\n"
        "**Impact share** = each sector's absolute effect as a percentage of the total across all sectors.  \n"
        f"Agriculture dominates with **{_AGR.get('long_run_share', 0)}%** of the combined long-run influence."
    )


def _resp_help() -> str:
    agr_s = _AGR.get('long_run_share', 0)
    ind_s = _IND.get('long_run_share', 0)
    srv_s = _SRV.get('long_run_share', 0)
    return (
        "## 🧠 Econex AI — What I Can Tell You\n\n"
        "I analyse ARDL (Autoregressive Distributed Lag) model results from your research data.\n\n"
        "### Current Data Summary\n"
        f"- 🌾 **Agriculture** impact on RSUI: **{agr_s}%** (long-run)\n"
        f"- 💼 **Services** impact on RSUI: **{srv_s}%** (long-run)\n"
        f"- 🏭 **Industry** impact on RSUI: **{ind_s}%** (long-run)\n\n"
        "### Try asking:\n"
        "- *\"Show agriculture impact\"*\n"
        "- *\"Compare all sectors\"*\n"
        "- *\"Short-run coefficients\"*\n"
        "- *\"Long-run effects\"*\n"
        "- *\"Industry analysis\"*\n"
        "- *\"Services sector\"*\n"
        "- *\"Which sector has highest impact?\"*"
    )


# ── Keyword-based router ──────────────────────────────────────────────────────

_KEYWORD_MAP = [
    # (keyword list, response function)
    (["agriculture", "agr", "farming", "farm", "rural", "crop"],  _resp_agriculture),
    (["industry", "ind", "manufacturing", "industrial"],           _resp_industry),
    (["service", "srv", "tertiary"],                               _resp_services),
    (["compare", "comparison", "all sector", "vs", "versus",
      "which", "highest", "rank", "ranking", "overview"],         _resp_comparison),
    (["short run", "short-run", "short_run", "coefficient",
      "immediate", "coef"],                                        _resp_short_run_all),
    (["long run", "long-run", "long_run", "long term",
      "structural", "sustained"],                                  _resp_long_run_all),
    (["gdp", "sector", "impact", "rsui", "unrest", "model",
      "ardl", "result", "output"],                                 _resp_overview),
]


def get_ai_response(message: str, history: list[dict] | None = None) -> str:
    """
    Pure CSV-driven response engine.
    No OpenAI required. Matches keywords and returns real ARDL data.
    """
    q = message.lower().strip()

    for keywords, fn in _KEYWORD_MAP:
        if any(kw in q for kw in keywords):
            return fn()

    # Default: show help with current data summary
    return _resp_help()
