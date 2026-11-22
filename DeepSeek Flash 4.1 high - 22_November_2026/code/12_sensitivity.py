"""Step 12: pre-specified sensitivity analyses S1-S10 (+S11 cluster-level check)."""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

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

# ---------------------------------------------------------------- helper machinery
def loyo_oof(data, xcols, ycol="y", quad=None, cluster_col="wgroup"):
    """Leave-one-year-out OOF predictions for an arbitrary column set."""
    y = data[ycol].values.astype(float)
    oof = np.full(len(data), np.nan)
    for yr in sorted(data["year"].unique()):
        te = (data["year"] == yr).values
        tr = ~te
        if y[tr].min() == y[tr].max():
            continue
        Xtr = data.loc[tr, xcols].astype(float)
        Xte = data.loc[te, xcols].astype(float)
        if quad is not None:
            c = float(Xtr[quad].mean())
            Xtr = Xtr.assign(sq=(Xtr[quad] - c) ** 2)
            Xte = Xte.assign(sq=(Xte[quad] - c) ** 2)
        res = fm.fit_logit(Xtr, y[tr])
        oof[te] = fm.predict(res, Xte)
    return oof


def summarize_oof(data, oof, label, ycol="y"):
    ok = ~np.isnan(oof)
    y = data[ycol].values[ok]
    pr = oof[ok]
    a = fm.auc(y, pr)
    lo, hi, _ = fm.cluster_bootstrap_metric(y, pr, data["wgroup"].values[ok],
                                            metric="auc", n_boot=600)
    ci, sl, _, _ = fm.calib(y, pr)
    return {"analysis": label, "n": int(ok.sum()), "events": int(y.sum()),
            "auc": a, "auc_lo": lo, "auc_hi": hi,
            "brier": fm.brier(y, pr), "calib_int": ci, "calib_slope": sl}


rows = []

# ============================================================ baseline (primary)
v = fs.build_vars(flat)
d = fs.design_frame(df, v)
base_oof = loyo_oof(d, ["rh90_per10h", "t30_per10h"])
rows.append(summarize_oof(d, base_oof, "reference: M2, EPI=S>=5%, window -7..0"))

p("=" * 100)
p("S1. OUTCOME CUT-POINT")
p("=" * 100)
for thr in (1.0, 5.0, 10.0, 20.0):
    dd = d.copy()
    dd["y"] = (dd["S"] >= thr).astype(int)
    oof = loyo_oof(dd, ["rh90_per10h", "t30_per10h"])
    r = summarize_oof(dd, oof, f"S1 cut-point S>={thr:g}%")
    rows.append(r)
    p(f"  S>={thr:g}%: events={r['events']}, OOF AUC={r['auc']:.3f} "
      f"[{r['auc_lo']:.3f},{r['auc_hi']:.3f}], Brier={r['brier']:.3f}, "
      f"calib slope={r['calib_slope']:.3f}")

p("\n" + "=" * 100)
p("S2/S3. EXPOSURE WINDOW (warm-wet hours + heat hours; counts per day)")
p("=" * 100)
p("  NOTE: the 24-h RH>=90 count exists only for the -7..0 and -20..0 windows in this")
p("  release, so the window ladder uses the warm-wet-hours concept, which exists for")
p("  every window from -5 to -15 d (and the -20..0 comparison uses RH>=90 instead).")
win_rows = []
for (ws, we) in [(-5, 0), (-7, 0), (-10, 0), (-14, 0), (-15, 0), (-20, 0)]:
    vv = fm.vars_for_window(flat, ws, we)
    ndays = we - ws + 1
    moist = vv.get("ww980_h")
    concept = "warm-wet h (9-30C & RH>=80)"
    if moist is None:
        moist = vv.get("rh90_h")
        concept = "RH>=90 h"
    if moist is None or vv.get("t30_h") is None:
        p(f"  window {ws}..{we}: skipped (moisture={moist}, t30={vv.get('t30_h')})")
        continue
    dd = pd.DataFrame({
        "y": d["y"].values,
        "year": d["year"].values, "wgroup": d["wgroup"].values,
        "moist_per10h": df[moist].astype(float).values / 10.0,
        "t30_per10h": df[vv["t30_h"]].astype(float).values / 10.0,
        "moist_per_day": df[moist].astype(float).values / ndays,
        "t30_per_day": df[vv["t30_h"]].astype(float).values / ndays,
        "S": d["S"].values,
    })
    oof = loyo_oof(dd, ["moist_per10h", "t30_per10h"])
    r = summarize_oof(dd, oof, f"S2 window {ws}..{we} d ({ndays} d; {concept})")
    rows.append(r)
    res = fm.fit_logit(dd[["moist_per_day", "t30_per_day"]], dd["y"].values,
                       cluster=dd["wgroup"].values)
    ci = np.exp(np.asarray(res.conf_int())[1:])
    ors = np.exp(np.asarray(res.params)[1:])
    p(f"  {ws:>3}..{we:<4}({ndays:2d} d, {concept:26s}): OOF AUC={r['auc']:.3f} "
      f"[{r['auc_lo']:.3f},{r['auc_hi']:.3f}]; OR per +1 h/d: "
      f"moisture={ors[0]:.3f} ({ci[0,0]:.3f}-{ci[0,1]:.3f}), "
      f"T>30={ors[1]:.3f} ({ci[1,0]:.3f}-{ci[1,1]:.3f})")

p("\n  moisture-metric swap within the -7..0 d window (1-term models, LOYO):")
for label, col in [("RH>=90 h", v["rh90_h"]), ("mean RH", v["meanRH"]),
                   ("warm-wet 9-30C & RH>=80 h", v["ww980_h"])]:
    dd = pd.DataFrame({"y": d["y"].values, "year": d["year"].values,
                       "wgroup": d["wgroup"].values, "S": d["S"].values,
                       "x": df[col].astype(float).values})
    oof = loyo_oof(dd, ["x"])
    r = summarize_oof(dd, oof, f"S2c moisture metric: {label}")
    rows.append(r)
    p(f"    {label:28s} OOF AUC={r['auc']:.3f} [{r['auc_lo']:.3f},{r['auc_hi']:.3f}]")

p("\n" + "=" * 100)
p("S4. 12-h 'OVERNIGHT' MOISTURE INSTEAD OF 24-h")
p("=" * 100)
# overnight RH>=90 hours at -7..0 exists as RH.G90.PRE7.12H
overnight = [c for c in df.columns if c.startswith("RH.G90.PRE7.12H")]
p("overnight columns found:", overnight)
if overnight:
    dd = pd.DataFrame({"y": d["y"].values, "year": d["year"].values,
                       "wgroup": d["wgroup"].values, "S": d["S"].values,
                       "rh90_12h_per10h": df[overnight[0]].astype(float).values / 10.0})
    oof = loyo_oof(dd, ["rh90_12h_per10h"])
    r = summarize_oof(dd, oof, "S4 overnight RH>=90 h (-7..0) alone")
    rows.append(r)
    p(f"  overnight-only 1-term: OOF AUC={r['auc']:.3f} [{r['auc_lo']:.3f},{r['auc_hi']:.3f}]")
    # and with 24h term for comparison
    dd["rh90_24h_per10h"] = d["rh90_per10h"].values
    oof24 = loyo_oof(dd, ["rh90_24h_per10h"])
    r24 = summarize_oof(dd, oof24, "S4b 24h RH>=90 h (-7..0) alone (comparison)")
    rows.append(r24)
    p(f"  24h-only 1-term: OOF AUC={r24['auc']:.3f} "
      f"[{r24['auc_lo']:.3f},{r24['auc_hi']:.3f}]")

p("\n" + "=" * 100)
p("S5/S6. INFLUENCE OF DISEASE-FREE COHORT AND OF THE LARGEST YEAR")
p("=" * 100)
allzero_years = sorted(df.groupby("year")["S"].max().loc[
    lambda s: s == 0].index.tolist())
p("  years with S == 0 in every plot:", allzero_years)
keep = ~d["year"].isin(allzero_years)
sub = d[keep].reset_index(drop=True)
oof = loyo_oof(sub, ["rh90_per10h", "t30_per10h"])
r = summarize_oof(sub, oof, "S5 drop all-zero years")
rows.append(r)
p(f"  drop all-zero years (n={r['n']}): OOF AUC={r['auc']:.3f} "
  f"[{r['auc_lo']:.3f},{r['auc_hi']:.3f}]")
sub = d[d["year"] != 2009].reset_index(drop=True)
oof = loyo_oof(sub, ["rh90_per10h", "t30_per10h"])
r = summarize_oof(sub, oof, "S6 exclude 2009 (n=167 plots)")
rows.append(r)
p(f"  exclude 2009 (n={r['n']}): OOF AUC={r['auc']:.3f} "
  f"[{r['auc_lo']:.3f},{r['auc_hi']:.3f}]")

p("\n" + "=" * 100)
p("S7. DELETE-ONE-TRIAL JACKKNIFE ON M2 AND M5 COEFFICIENTS")
p("=" * 100)
for name, cols in (("M2", ["rh90_per10h", "t30_per10h"]),
                   ("M5", ["ww980_per10h", "t30_per10h"])):
    full = fm.fit_logit(d[cols], d["y"].values, cluster=d["wgroup"].values)
    b0 = np.asarray(full.params)[1:]
    jk = []
    for tr in sorted(df["trial"].unique()):
        m = (df["trial"] != tr).values
        try:
            r = fm.fit_logit(d.loc[m, cols], d["y"].values[m])
            jk.append(np.asarray(r.params)[1:])
        except Exception:  # noqa: BLE001
            continue
    jk = np.array(jk)
    p(f"  {name}: full-sample coefs {np.round(b0, 4)}; jackknife range "
      f"{np.round(jk.min(0), 4)} .. {np.round(jk.max(0), 4)}; "
      f"sign flips: {[bool((np.sign(jk[:, i]) != np.sign(b0[i])).any()) for i in range(len(b0))]}")

p("\n" + "=" * 100)
p("S8. CONTINUOUS OUTCOME CHECK (fractional logit on S/100, cluster-robust)")
p("=" * 100)
frac = d["S"].values / 100.0
X = sm.add_constant(d[["rh90_per10h", "t30_per10h"]].astype(float).values)
m = sm.GLM(frac, X, family=sm.families.Binomial()).fit(
    cov_type="cluster", cov_kwds={"groups": d["wgroup"].values})
p("  coefficients (logit scale) with cluster-robust SE:")
names = ["Intercept", "rh90_per10h", "t30_per10h"]
for nm, b, se, pv in zip(names, m.params, m.bse, m.pvalues):
    p(f"    {nm:14s} {b:+.4f}  se={se:.4f}  p={pv:.4g}  OR={np.exp(b):.4f}")
p(f"  Spearman(predicted, S) = {pd.Series(m.fittedvalues).corr(d['S'], method='spearman'):.3f}")
r = {"analysis": "S8 fractional logit OR rh90_per10h", "auc": np.nan,
     "auc_lo": np.nan, "auc_hi": np.nan, "n": len(d), "events": int(d["y"].sum()),
     "brier": np.nan, "calib_int": np.nan, "calib_slope": np.nan}
rows.append(r)

p("\n" + "=" * 100)
p("S10. M4 WITH corn MISSING CODED AS ABSENT vs COMPLETE-CASE")
p("=" * 100)
d_imp = d.copy()
d_imp["corn"] = d_imp["corn"].fillna(0.0)
for lab, dd in (("complete-case", d.dropna(subset=["corn"])), ("NA->0", d_imp)):
    res = fm.fit_logit(dd[["rh90_per10h", "t30_per10h", "resist_ord", "corn"]],
                       dd["y"].values, cluster=dd["wgroup"].values)
    p(f"  {lab:14s} n={len(dd)} coefs="
      f"{np.round(np.asarray(res.params)[1:], 4)}")

p("\n" + "=" * 100)
p("S11. CLUSTER-LEVEL CHECK (one row per weather group, fractional outcome)")
p("=" * 100)
g = d.dropna(subset=["corn"]).groupby("wgroup").agg(
    y=("y", "mean"), rh90=("rh90_per10h", "mean"), t30=("t30_per10h", "mean"),
    meanT=("meanT", "mean"), n=("y", "size"))
p(f"  n groups={len(g)}; between-group event fraction: mean={g['y'].mean():.3f}")
res = fm.fit_logit(g[["rh90", "t30"]], g["y"].values)
p("  group-level fractional logit coefficients (unweighted):",
  np.round(np.asarray(res.params), 4),
  " p:", np.round(np.asarray(res.pvalues), 4))
w = g["n"].values
res2 = sm.GLM(g["y"].values, sm.add_constant(g[["rh90", "t30"]].values),
              family=sm.families.Binomial(), freq_weights=w).fit()
p("  group-level weighted (by n plots) coefficients:",
  np.round(np.asarray(res2.params), 4), " p:", np.round(np.asarray(res2.pvalues), 4))

sens = pd.DataFrame(rows)
sens.to_csv(os.path.join(env.OUT, "sensitivity.csv"), index=False)
p("\n" + "=" * 100)
p("SUMMARY OF ALL OOF SENSITIVITY ANALYSES")
p("=" * 100)
p(sens[["analysis", "n", "events", "auc", "auc_lo", "auc_hi", "brier",
        "calib_slope"]].round(3).to_string(index=False))

with open(os.path.join(env.OUT, "12_sensitivity.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/12_sensitivity.txt")
