import os
import re
import pandas as pd
import numpy as np

INPUT_DIR = "finalresults"  # change this to your folder name
OUTPUT_CSV = "relationship_table.csv"

def infer_indep(filename: str) -> str:
    f = filename.lower()
    if "unemployment" in f and "gov" not in f:
        return "unemployment"
    if "total_expenditure" in f:
        return "total_expenditure"
    if "gov_exp" in f or "gov exp" in f:
        return "government_expenditure"
    if "wage" in f:
        return "wage"
    if "gdp" in f:
        return "gdp"
    if "pce" in f:
        return "pce"
    return "x"

def infer_horizon(filename: str, cols) -> str:
    f = filename.lower()
    if "long" in f and "short" not in f:
        return "long_run"
    if "short" in f:
        return "short_run"
    if "long_run_effect" in cols:
        return "long_run"
    return "short_run"

def pick_group_col(cols):
    # prefer label-like columns, then common names
    label_cols = [c for c in cols if c.endswith("_label")]
    if label_cols:
        return label_cols[0]
    for c in ["sector_name", "category_name", "category_label", "age_group_label", "edu_label", "exp_type_label", "category_group","total_category_label"]:
        if c in cols:
            return c
    return None

def pick_coef_p(cols):
    if "coef" in cols and "pvalue" in cols:
        return "coef", "pvalue"
    coef_cols = [c for c in cols if c.endswith("_coef")]
    pv_cols = [c for c in cols if c.endswith("_pvalue")]
    if coef_cols and pv_cols:
        for cc in coef_cols:
            pref = cc[:-5]
            pv = pref + "_pvalue"
            if pv in cols:
                return cc, pv
        return coef_cols[0], pv_cols[0]
    return None, None

def main():
    rows = []
    for fn in os.listdir(INPUT_DIR):
        if not fn.lower().endswith(".csv"):
            continue

        path = os.path.join(INPUT_DIR, fn)
        df = pd.read_csv(path)
        cols = df.columns.tolist()

        indep = infer_indep(fn)
        horizon = infer_horizon(fn, cols)
        group_col = pick_group_col(cols)
        coef_col, pv_col = pick_coef_p(cols)
        has_long = "long_run_effect" in cols

        for _, r in df.iterrows():
            group_label = str(r[group_col]) if group_col else ""
            group_type = group_col.replace("_label", "") if group_col else ""

            n_obs = r.get("n_obs", np.nan)
            aic = r.get("aic", np.nan)
            bic = r.get("bic", np.nan)
            status = r.get("status", "")

            if has_long:
                coef = float(r["long_run_effect"]) if pd.notna(r["long_run_effect"]) else np.nan
                pvalue = np.nan
            else:
                coef = float(r[coef_col]) if coef_col and pd.notna(r[coef_col]) else np.nan
                pvalue = float(r[pv_col]) if pv_col and pd.notna(r[pv_col]) else np.nan

            direction = "positive" if (pd.notna(coef) and coef > 0) else "negative" if (pd.notna(coef) and coef < 0) else "zero/unknown"

            if pd.notna(pvalue):
                sig = "significant" if pvalue < 0.05 else "not significant"
                desc = f"{horizon.replace('_',' ')} effect of {indep} on RSUI for {group_label}: {direction} ({sig}; coef={coef:.6g}, p={pvalue:.3g})."
            else:
                desc = f"{horizon.replace('_',' ')} effect estimate of {indep} on RSUI for {group_label}: {direction} (estimate={coef:.6g}; p-value not provided in this file)."

            rows.append({
                "dep_var": "RSUI",
                "indep_var": indep,
                "group_type": group_type,
                "group_label": group_label,
                "horizon": horizon,
                "effect_value": coef,
                "pvalue": pvalue,
                "n_obs": n_obs,
                "status": status,
                "aic": aic,
                "bic": bic,
                "source_file": fn,
                "description": desc
            })

    out = pd.DataFrame(rows).sort_values(["indep_var","horizon","group_label"])
    out.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote {len(out)} rows -> {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
