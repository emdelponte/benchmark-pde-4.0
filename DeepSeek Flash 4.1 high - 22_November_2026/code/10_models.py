"""Step 10: fit the pre-specified models on the full data, report estimates with
cluster-robust uncertainty, collinearity diagnostics, and apparent performance.

Model estimates only. Validation is in 11_validate.py; sensitivity in 12_*.
"""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor

import fhb_env as env
import fhb_model as fm
import fhb_specs as fs

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
out = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


df, flat = fm.load()
v = fs.build_vars(flat)
p("window variables resolved for -7..0 d:")
for k, val in v.items():
    p(f"  {k:10s} -> {val}")
d = fs.design_frame(df, v)

p("\n" + "=" * 100)
p("A. DESIGN SUMMARY")
p("=" * 100)
p("n =", len(d), " events(EPI=1):", int(d["y"].sum()), " prevalence:",
  round(d["y"].mean(), 4))
p("distinct weather groups:", d["wgroup"].nunique(),
  " trials:", df["trial"].nunique())
p("\npredictor summary:")
p(d[["rh90_per10h", "t30_per10h", "meanT", "meanRH", "ww980_per10h",
     "resist_ord", "corn"]].describe().round(3).to_string())

p("\n" + "=" * 100)
p("B. COLLINEARITY OF THE PRIMARY TERMS (environment level)")
p("=" * 100)
first = ~d["wgroup"].duplicated()
cm = d.loc[first, ["rh90_per10h", "t30_per10h", "meanT", "meanRH", "ww980_per10h"]].corr(
    method="spearman")
p(cm.round(2).to_string())
cm.to_csv(os.path.join(env.OUT, "model_correlations.csv"))

Xv = d[["rh90_per10h", "t30_per10h", "meanT"]].astype(float)
Xv = Xv.assign(const=1.0)
vif = pd.DataFrame({
    "term": Xv.columns,
    "VIF": [variance_inflation_factor(Xv.values, i) for i in range(Xv.shape[1])],
})
p("\nVIF for the 3-term specification (M3):")
p(vif.round(2).to_string())

p("\n" + "=" * 100)
p("C. MODEL ESTIMATES (MLE, cluster-robust SE by weather group)")
p("=" * 100)
est_rows = []
fits = {}
for name in fs.SPECS:
    cols = fs.SPECS[name]["cols"]
    if name == "M4":
        sub = d.dropna(subset=["corn"])
    else:
        sub = d
    if name == "M0":
        # prevalence-only model: no estimation needed
        pr = sub["y"].mean()
        fits[name] = None
        est_rows.append({"model": name, "term": "Intercept",
                         "coef": np.log(pr / (1 - pr)), "se": np.nan, "z": np.nan,
                         "p": np.nan, "OR": pr / (1 - pr), "OR_lo": np.nan,
                         "OR_hi": np.nan, "n": len(sub),
                         "events": int(sub["y"].sum())})
        continue
    if fs.SPECS[name]["kind"] == "ridge":
        # point estimates from the ridge fit (standardised scale) are not ORs; skip
        Xtr, ytr, _ = fs.make_xy(name, sub, sub)
        C = fs.choose_C(Xtr, ytr, sub["year"].values)
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        sc = StandardScaler().fit(Xtr)
        m = LogisticRegression(C=C, l1_ratio=0.0, solver="lbfgs", max_iter=2000)
        m.fit(sc.transform(Xtr), ytr)
        fits[name] = (m, sc, C)
        p(f"\n-- {name} {fs.SPECS[name]['desc']} --")
        p(f"   penalty C={C}; coefficients on standardised scale (OR per 1 SD):")
        for c, b in zip(Xtr.columns, m.coef_[0]):
            p(f"   {c:15s} beta={b:+.4f}  OR={np.exp(b):.3f}")
        continue
    X, y, _ = fs.make_xy(name, sub, sub)
    res = fm.fit_logit(X, y, cluster=sub["wgroup"].values)
    fits[name] = res
    t = fm.or_table(res, list(X.columns), cluster_label="weather group")
    t["model"] = name
    t["n"] = len(sub)
    t["events"] = int(sub["y"].sum())
    est_rows.append(t)
    p(f"\n-- {name}: {fs.SPECS[name]['desc']}  (n={len(sub)}, events={int(sub['y'].sum())}, "
      f"params={len(X.columns)}) --")
    p(t.round(4).to_string(index=False))
    p(f"   log-likelihood={res.llf:.2f}  AIC={res.aic:.2f}  "
      f"pseudo-R2(McFadden)={1 - res.llf / res.llnull:.3f}")

est = pd.concat([e if isinstance(e, pd.DataFrame) else pd.DataFrame([e])
                 for e in est_rows], ignore_index=True)
est.to_csv(os.path.join(env.OUT, "model_estimates.csv"), index=False)

p("\n" + "=" * 100)
p("D. APPARENT (IN-SAMPLE) PERFORMANCE  -- for the optimism gap only")
p("=" * 100)
app = []
for name in fs.SPECS:
    sub = d.dropna(subset=["corn"]) if name == "M4" else d
    if name == "M7":
        Xtr, ytr, _ = fs.make_xy(name, sub, sub)
        from sklearn.preprocessing import StandardScaler
        m, sc, C = fits[name]
        pr = m.predict_proba(sc.transform(Xtr))[:, 1]
    elif name == "M0":
        pr = np.full(len(sub), sub["y"].mean())
    else:
        res = fits[name]
        pr = fm.predict(res, sub[fs.SPECS[name]["cols"]]
                        if fs.SPECS[name]["kind"] == "plain"
                        else sub[["rh90_per10h", "t30_per10h"]].assign(
                            rh90_sq=(sub["rh90_per10h"] - sub["rh90_per10h"].mean()) ** 2))
    a = fm.auc(sub["y"], pr)
    b = fm.brier(sub["y"], pr)
    ci, sl, _, _ = fm.calib(sub["y"], pr)
    app.append({"model": name, "n_params": len(fs.SPECS[name]["cols"]),
                "apparent_auc": a, "apparent_brier": b,
                "calib_intercept": ci, "calib_slope": sl})
appdf = pd.DataFrame(app)
appdf.to_csv(os.path.join(env.OUT, "apparent_performance.csv"), index=False)
p(appdf.round(4).to_string(index=False))

p("\n" + "=" * 100)
p("E. EFFECT SIZE CORNER: M2 odds ratios per 10 h, and per 1 day")
p("=" * 100)
r = fits["M2"]
b1, b2 = float(r.params[1]), float(r.params[2])
p(f"RH>=90 h: OR per 10 h = {np.exp(b1):.3f}; per 24 h = {np.exp(b1*2.4):.3f}")
p(f"T>30 h  : OR per 10 h = {np.exp(b2):.3f}; per 24 h = {np.exp(b2*2.4):.3f}")
p("predicted risk at combinations (rh90 hours, t30 hours) over the 8-day window:")
grid = pd.DataFrame({"rh90_per10h": [0.5, 1.5, 3.0, 5.0, 8.0]})
b0 = float(r.params[0])


def _p(x1, x2):
    return 1.0 / (1.0 + np.exp(-(b0 + b1 * x1 + b2 * x2)))


grid["p_heat0h"] = _p(grid["rh90_per10h"], 0.0)
grid["p_heat20h"] = _p(grid["rh90_per10h"], 2.0)
grid["p_heat40h"] = _p(grid["rh90_per10h"], 4.0)
grid["rh90_hours_window"] = grid["rh90_per10h"] * 10
p(grid.round(4).to_string(index=False))

with open(os.path.join(env.OUT, "10_models.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/10_models.txt")
