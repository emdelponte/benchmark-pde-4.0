"""Step 7: candidate predictor set -- availability, redundancy, univariate signal.

Descriptive only: nothing here is used to fit the final model or to evaluate it.
Univariate statistics are used to check that the a-priori candidate families are
not degenerate, not to pick a winner by AUC.
"""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd
from scipy import stats

import fhb_env as env

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)

df = pd.read_pickle(os.path.join(env.OUT, "fhb_raw2.pkl"))
flat = pd.read_csv(os.path.join(env.OUT, "yaml_columns_flat.csv"))
meta = flat.set_index("name")
y = (df["S"] >= 5).astype(int).values

# one representative weather vector per distinct weather block -> environment-level
DESIGN = {"id", "year", "state", "fdate", "type", "resist", "corn", "S"}
wcols = [c for c in df.columns
         if c in meta.index and c not in DESIGN and df[c].dtype.kind in "if"]
wx = df[wcols].astype(float)
vec_id = wx.astype(str).agg("|".join, axis=1)
env_idx = ~vec_id.duplicated()
print("plots:", len(df), " distinct weather vectors:", int(env_idx.sum()))


def find(desc_like, ws, we):
    """Find variable names matching a description substring and window."""
    m = meta[(meta["window_start_day"] == ws) & (meta["window_end_day"] == we)]
    m = m[m["description"].str.contains(desc_like, case=False, na=False,
                                        regex=True)]
    return m.index.tolist()


groups = {
    "mean T (24h)": r"^Mean daily T \(degC\)",
    "mean RH (24h)": r"^Mean daily RH \(%\)",
    "mean RH overnight (12h)": r"^Mean overnight RH",
    "mean VPD (24h)": r"^Mean daily VPD \(kPa\)",
    "mean VPD overnight (12h)": r"^Mean overnight VPD",
    "mean TDD (24h)": r"^Mean daily TDD \(degC\)",
    "mean dewpoint (24h)": r"^Mean daily D \(degC\)",
    "hr RH>=90 (24h)": r"^No\. hr \(RH >= 90%\)",
    "hr RH>=80 (24h)": r"^No\. hr \(RH >= 80%\)",
    "hr 15-30C & RH>=80 (24h)": r"^No\. hr \(15degC <= T <= 30degC & RH >= 80%\)",
    "hr 15-30C & RH>=90 (24h)": r"^No\. hr \(15degC <= T <= 30degC & RH >= 90%\)",
    "hr 9-30C & RH>=80 (24h)": r"^No\. hr \(9degC <= T <= 30degC & RH >= 80%\)",
    "hr 9-30C & RH>=90 (24h)": r"^No\. hr \(9degC <= T <= 30degC & RH >= 90%\)",
    "hr T>=15 (24h)": r"^No\. hr \(T >= 15degC\)",
    "hr T<15 (24h)": r"^No\. hr \(T < 15degC\)",
    "hr T>30 (24h)": r"^No\. hr \(T > 30degC\)",
    "mean T overnight (12h)": r"^Mean overnight T\b",
}
windows = [(-5, 0), (-7, 0), (-10, 0), (-14, 0), (-15, 0), (-20, 0)]

rows = []
for win in windows:
    for gname, pat in groups.items():
        hits = find(pat, win[0], win[1])
        for h in hits:
            d = {"group": gname, "window": f"{win[0]}..{win[1]}", "var": h,
                 "desc": meta.loc[h, "description"] if h in meta.index else ""}
            if h not in df.columns:
                d["status"] = "absent"
                rows.append(d)
                continue
            x = df[h].astype(float)
            d["status"] = "present"
            d["n"] = int(x.notna().sum())
            d["mean"] = x.mean()
            d["sd"] = x.std()
            d["min"] = x.min()
            d["max"] = x.max()
            # Spearman with binary outcome (descriptive)
            ok = x.notna().values
            rho, p = stats.spearmanr(x[ok], y[ok])
            d["spearman_rho_vs_epi5"] = rho
            d["spearman_p"] = p
            # environment-level (unique weather vectors)
            rho_e, p_e = stats.spearmanr(x[env_idx], y[env_idx.values])
            d["rho_env_level"] = rho_e
            rows.append(d)

cand = pd.DataFrame(rows)
cand.to_csv(os.path.join(env.OUT, "candidate_screen.csv"), index=False)
print("\n== candidate availability by group x window ==")
avail = cand.assign(present=cand["status"] == "present").pivot_table(
    index="group", columns="window", values="present", aggfunc="max")
print(avail.to_string())

print("\n== candidate descriptors (present only), sorted by |rho| ==")
show = cand[cand["status"] == "present"].copy()
show = show.sort_values("spearman_rho_vs_epi5", key=lambda s: -s.abs())
print(show[["group", "window", "var", "mean", "sd", "min", "max",
            "spearman_rho_vs_epi5", "spearman_p", "rho_env_level"]]
      .round(3).to_string(index=False))

# correlation structure within the 7-day window and across the moisture family
print("\n== Spearman correlations among -7..0 candidates (environment level) ==")
sel = cand[(cand["window"] == "-7..0") & (cand["status"] == "present")]["var"].tolist()
cm = df.loc[env_idx.values, sel].astype(float).corr(method="spearman")
print(cm.round(2).to_string())

print("\n== Spearman correlations across windows for the combined warm-wet term ==")
ww = [v for v in df.columns if v.startswith("TRH.15T30nRHG80")]
print(len(ww), "vars; sample:", ww[:6])
cm2 = df.loc[env_idx.values, ww].astype(float).corr(method="spearman")
print(cm2.round(2).to_string())
