"""Step 13: confounding diagnostics -- is the weather signal between-year or
within-year, and what happens when year / state effects are absorbed?

These are explanatory models with many nuisance parameters; they are NOT candidate
prediction models (the parameter budget in analysis_plan.md still governs prediction).
"""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

import fhb_env as env
import fhb_model as fm
import fhb_specs as fs

pd.set_option("display.width", 250)
out = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


df, flat = fm.load()
v = fs.build_vars(flat)
d = fs.design_frame(df, v)
d["state"] = df["state"].astype(str).values
d["trial"] = df["trial"].values
d["corn"] = d["corn"].fillna(0.0)
d["meanRH"] = df[v["meanRH"]].astype(float).values

p("=" * 100)
p("A. WHERE DOES THE VARIATION LIVE? (variance decomposition of key variables)")
p("=" * 100)
for col in ("ww980_per10h", "rh90_per10h", "meanRH", "t30_per10h", "meanT", "y"):
    x = d[col].astype(float)
    tot = x.var()
    by_year = x.groupby(d["year"]).transform("mean").var()
    by_state = x.groupby(d["state"]).transform("mean").var()
    p(f"  {col:14s} total var={tot:8.4f}  between-year={by_year/tot:5.1%}  "
      f"between-state={by_state/tot:5.1%}")

p("\n  year-level ecological correlation (32 years, mean weather vs event fraction):")
yr = d.groupby("year").agg(y=("y", "mean"), ww=("ww980_per10h", "mean"),
                           rh=("rh90_per10h", "mean"), mrh=("meanRH", "mean"),
                           n=("y", "size"))
for c in ("ww", "rh", "mrh"):
    p(f"    {c:4s}: Pearson r = {yr['y'].corr(yr[c]):+.3f}  "
      f"(weighted by plots: {np.corrcoef(yr['y'], yr[c])[0,1]:+.3f})")

p("\n  trial-level (492) correlation of mean weather vs event fraction:")
tr = d.groupby("trial").agg(y=("y", "mean"), ww=("ww980_per10h", "mean"),
                            rh=("rh90_per10h", "mean"), mrh=("meanRH", "mean"))
for c in ("ww", "rh", "mrh"):
    p(f"    {c:4s}: Pearson r = {tr['y'].corr(tr[c]):+.3f}")

p("\n" + "=" * 100)
p("B. WEATHER COEFFICIENT WITH YEAR AND/OR STATE EFFECTS ABSORBED")
p("=" * 100)
p("  (GLM binomial, cluster-robust SE by weather group; coefficients on logit scale)")


def fit_fe(xcols, fe=(), label=""):
    X = d[list(xcols)].astype(float).copy()
    parts = [X]
    if "year" in fe:
        yd = pd.get_dummies(d["year"].astype(str), prefix="yr", drop_first=True).astype(float)
        parts.append(yd)
    if "state" in fe:
        sd = pd.get_dummies(d["state"], prefix="st", drop_first=True).astype(float)
        parts.append(sd)
    Xf = pd.concat(parts, axis=1)
    Xf = sm.add_constant(Xf.values)
    m = sm.GLM(d["y"].values.astype(float), Xf, family=sm.families.Binomial()).fit(
        cov_type="cluster", cov_kwds={"groups": d["wgroup"].values})
    b = np.asarray(m.params)[1:1 + len(xcols)]
    se = np.asarray(m.bse)[1:1 + len(xcols)]
    pv = np.asarray(m.pvalues)[1:1 + len(xcols)]
    return b, se, pv, label, m


for xcols, nm in ((["ww980_per10h"], "warm-wet hours"),
                  (["meanRH"], "mean RH"),
                  (["rh90_per10h", "t30_per10h"], "RH>=90 h + T>30 h")):
    p(f"\n  -- exposure: {nm} --")
    for fe, lab in (((), "unadjusted"), (("year",), "+ year FE"),
                    (("state",), "+ state FE"),
                    (("year", "state"), "+ year FE + state FE")):
        b, se, pv, _, m = fit_fe(xcols, fe, lab)
        s = ", ".join(f"{x:+.4f} (se {e:.4f}, p={q:.3g})" for x, e, q in zip(b, se, pv))
        p(f"    {lab:22s} n_par={int(m.df_model)+1:3d}  {s}")

p("\n" + "=" * 100)
p("C. INFLUENCE OF 2009 AND OF THE DENSEST STATE ON THE WEATHER COEFFICIENT")
p("=" * 100)
for drop, lab in ((None, "all data"), (2009, "drop 2009"),
                  ("ND", "drop ND (265 plots)"), ("ND+2009", "drop ND and 2009")):
    if drop is None:
        sub = d
    elif drop == "ND":
        sub = d[d["state"] != "ND"]
    elif drop == "ND+2009":
        sub = d[(d["state"] != "ND") & (d["year"] != 2009)]
    else:
        sub = d[d["year"] != drop]
    for xcols, nm in ((["meanRH"], "mean RH"), (["ww980_per10h"], "warm-wet h")):
        m = sm.GLM(sub["y"].values.astype(float),
                   sm.add_constant(sub[xcols].values.astype(float)),
                   family=sm.families.Binomial()).fit(
            cov_type="cluster", cov_kwds={"groups": sub["wgroup"].values})
        b = np.asarray(m.params)[1]
        p(f"  {lab:16s} {nm:12s}: coef={b:+.4f}  OR per SD="
          f"{np.exp(b*sub[xcols[0]].std()):.3f}  p={np.asarray(m.pvalues)[1]:.3g}  n={len(sub)}")

p("\n" + "=" * 100)
p("D. WITHIN-YEAR CONTRASTS (years with >=3 trials and both outcome classes)")
p("=" * 100)
rows = []
for yr, g in d.groupby("year"):
    if g["y"].nunique() < 2 or g["trial"].nunique() < 3:
        continue
    rows.append({"year": yr, "n": len(g), "trials": g["trial"].nunique(),
                 "event_frac": g["y"].mean(),
                 "meanRH_lo": g["meanRH"].min(), "meanRH_hi": g["meanRH"].max(),
                 "rh90_lo": g["rh90_per10h"].min(), "rh90_hi": g["rh90_per10h"].max()})
wy = pd.DataFrame(rows)
p(wy.round(3).to_string(index=False))
p(f"\n  years usable for within-year contrast: {len(wy)} of {d['year'].nunique()}")

with open(os.path.join(env.OUT, "13_confounding.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/13_confounding.txt")
