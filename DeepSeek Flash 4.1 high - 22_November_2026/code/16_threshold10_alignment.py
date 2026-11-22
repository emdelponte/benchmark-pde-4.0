"""Step 16 (POST HOC, after the literature search): align the primary models with the
published 'major epidemic' convention of FHB index >= 10% and with De Wolf et al. (2003)
predictors.

This script did not exist when the analysis plan was written and its numbers are NOT used
to change any pre-specified result. It exists so that the comparison with published work
is like-for-like.
"""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd

import fhb_env as env
import fhb_model as fm
import fhb_specs as fs

pd.set_option("display.width", 220)
out = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


df, flat = fm.load()
v = fs.build_vars(flat)
d = fs.design_frame(df, v)
d["TRH907"] = df["TRH907"].astype(float) / 10.0          # 15-30C & RH>=90, -7..0 d
d["meanRH"] = df[v["meanRH"]].astype(float)
d["rh90h"] = d["rh90_per10h"]
d["ww980"] = d["ww980_per10h"]
d["t30"] = d["t30_per10h"]
d["t1530h"] = df["TRH807"].astype(float) / 10.0  # 15-30C & RH>=80, -7..0 d (legacy name)
d["resist_ord"] = d["resist_ord"]
d["corn"] = d["corn"].fillna(0.0)

p("=" * 100)
p("0. EVENT COUNTS: does an independent 10% rule reproduce the published 273 epidemics?")
p("=" * 100)
for thr in (5, 10):
    p(f"  S >= {thr}%: {int((df['S'] >= thr).sum())} events of {len(df)}")
p("  Published (Shah et al. 2019b, Phil Trans R Soc B): 273 epidemics / 726 non-epidemics")
p("  -> the 273 matches S >= 10% exactly, i.e. the associated literature's binary outcome")
p("     is reconstructible from S and is NOT stored in the release.")


def loyo(data, cols, ycol="y10", quad=None):
    y = data[ycol].values.astype(float)
    oof = np.full(len(data), np.nan)
    for yr in sorted(data["year"].unique()):
        te = (data["year"] == yr).values
        tr = ~te
        if y[tr].min() == y[tr].max():
            continue
        Xtr = data.loc[tr, cols].astype(float)
        Xte = data.loc[te, cols].astype(float)
        if quad:
            c = float(Xtr[quad].mean())
            Xtr = Xtr.assign(sq=(Xtr[quad] - c) ** 2)
            Xte = Xte.assign(sq=(Xte[quad] - c) ** 2)
        r = fm.fit_logit(Xtr, y[tr])
        oof[te] = fm.predict(r, Xte)
    return oof


def summ(data, oof, label, ycol="y10"):
    ok = ~np.isnan(oof)
    y = data[ycol].values[ok]
    pr = oof[ok]
    lo, hi, _ = fm.cluster_bootstrap_metric(y, pr, data["wgroup"].values[ok],
                                            n_boot=800)
    ci, sl, _, _ = fm.calib(y, pr)
    return {"spec": label, "n": int(ok.sum()), "events": int(y.sum()),
            "auc": fm.auc(y, pr), "auc_lo": lo, "auc_hi": hi,
            "brier": fm.brier(y, pr), "calib_int": ci, "calib_slope": sl}


p("\n" + "=" * 100)
p("1. LOYO PERFORMANCE AT THE 10% 'MAJOR EPIDEMIC' THRESHOLD (post hoc)")
p("=" * 100)
d10 = d.copy()
d10["y10"] = (d10["S"] >= 10.0).astype(int)
rows = []
specs = [
    ("prevalence only", []),
    ("mean RH, -7..0 d (1 term)", ["meanRH"]),
    ("RH>=90 h, -7..0 d (1 term)", ["rh90h"]),
    ("De Wolf 2003: h 15-30C & RH>=90, -7..0 d", ["TRH907"]),
    ("h 15-30C & RH>=80, -7..0 d", ["t1530h"]),
    ("warm-wet h 9-30C & RH>=80 (M5 moisture term)", ["ww980"]),
    ("M1: RH>=90 h", ["rh90h"]),
    ("M2 (primary): RH>=90 h + T>30 h", ["rh90h", "t30"]),
    ("M5: warm-wet h + T>30 h", ["ww980", "t30"]),
    ("mean RH + T>30 h", ["meanRH", "t30"]),
    ("M3: M2 + mean T", ["rh90h", "t30", "meanT"]),
    ("M4: M2 + resistance + corn", ["rh90h", "t30", "resist_ord", "corn"]),
    ("mean RH + resistance + corn", ["meanRH", "resist_ord", "corn"]),
]
for label, cols in specs:
    if not cols:
        oof = np.full(len(d10), d10["y10"].mean())
    else:
        oof = loyo(d10, cols)
    r = summ(d10, oof, label)
    rows.append(r)
    p(f"  {label:46s} k={len(cols)}  AUC={r['auc']:.3f} [{r['auc_lo']:.3f},{r['auc_hi']:.3f}]  "
      f"Brier={r['brier']:.3f}  slope={r['calib_slope']:.2f}")

t = pd.DataFrame(rows)
t.to_csv(os.path.join(env.OUT, "threshold10_alignment.csv"), index=False)

p("\n" + "=" * 100)
p("2. SAME SPECIFICATIONS AT THE PRE-SPECIFIED 5% THRESHOLD (for contrast)")
p("=" * 100)
for label, cols in specs[1:]:
    oof = loyo(d, cols, ycol="y")
    r = summ(d, oof, label, ycol="y")
    p(f"  {label:46s} k={len(cols)}  AUC={r['auc']:.3f} [{r['auc_lo']:.3f},{r['auc_hi']:.3f}]  "
      f"Brier={r['brier']:.3f}")

p("\n" + "=" * 100)
p("3. IN-SAMPLE FIT OF THE DE WOLF (2003) PRE-ANTHESIS TERMS FOR INTERPRETATION")
p("=" * 100)
for cols, lab in ((["TRH907"], "h 15-30C & RH>=90 (7 d pre)"),
                  (["t1530h"], "h 15-30C & RH>=80 (7 d pre)"),
                  (["meanRH"], "mean RH (7 d pre)")):
    r = fm.fit_logit(d10[cols], d10["y10"].values, cluster=d10["wgroup"].values)
    b = np.asarray(r.params)[1]
    ci = np.exp(np.asarray(r.conf_int())[1])
    p(f"  {lab:34s} coef={b:+.4f}  OR per 10 h (or per % for RH)={np.exp(b):.3f} "
      f"[{ci[0]:.3f},{ci[1]:.3f}]  p={np.asarray(r.pvalues)[1]:.3g}")

with open(os.path.join(env.OUT, "16_threshold10.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/16_threshold10.txt")
