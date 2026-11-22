"""Model registry: the fixed, pre-specified specifications from analysis_plan.md §6.

Every specification is fitted with all estimation (centring, standardisation,
penalty choice) performed on the training data only.
"""
import fhb_env  # noqa: F401
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

import fhb_env as env
import fhb_model as fm

W = (-7, 0)  # primary exposure window: 7 d pre-anthesis to anthesis (8 days, 192 h)


def build_vars(flat):
    v = fm.vars_for_window(flat, *W)
    need = ["rh90_h", "t30_h", "meanT", "meanRH", "ww980_h"]
    missing = [k for k in need if v.get(k) is None]
    assert not missing, f"missing columns for {W}: {missing}"
    return v


def design_frame(df, v):
    """Primary design frame: released columns only, no derived weather summaries."""
    d = pd.DataFrame(index=df.index)
    d["y"] = (df["S"] >= 5.0).astype(int)
    d["rh90_per10h"] = df[v["rh90_h"]].astype(float) / 10.0
    d["t30_per10h"] = df[v["t30_h"]].astype(float) / 10.0
    d["meanT"] = df[v["meanT"]].astype(float)
    d["meanRH"] = df[v["meanRH"]].astype(float)
    d["ww980_per10h"] = df[v["ww980_h"]].astype(float) / 10.0
    d["resist_ord"] = df["resist_ord"].astype(float)
    d["corn"] = df["corn"].astype(float)
    d["year"] = df["year"].values
    d["state"] = df["state"].astype(str).values
    d["wgroup"] = df["wgroup"].values
    d["S"] = df["S"].values
    d["rh90_h"] = df[v["rh90_h"]].astype(float)
    d["t30_h"] = df[v["t30_h"]].astype(float)
    return d


SPECS = {
    "M0": dict(desc="intercept only (prevalence baseline)", cols=[], kind="plain"),
    "M1": dict(desc="wetness only: RH>=90 h (per 10 h)", cols=["rh90_per10h"], kind="plain"),
    "M2": dict(desc="PRIMARY: wetness + heat-stress hours",
               cols=["rh90_per10h", "t30_per10h"], kind="plain"),
    "M3": dict(desc="M2 + mean temperature",
               cols=["rh90_per10h", "t30_per10h", "meanT"], kind="plain"),
    "M4": dict(desc="M2 + cultivar resistance + corn residue",
               cols=["rh90_per10h", "t30_per10h", "resist_ord", "corn"], kind="plain"),
    "M5": dict(desc="alternative moisture concept: warm-wet hours + heat hours",
               cols=["ww980_per10h", "t30_per10h"], kind="plain"),
    "M6": dict(desc="M2 + quadratic wetness (centred)", cols=["rh90_per10h", "t30_per10h"],
               kind="quadratic"),
    "M7": dict(desc="ridge logistic on M3 predictors", cols=["rh90_per10h", "t30_per10h", "meanT"],
               kind="ridge"),
}


def make_xy(name, train, test):
    """X/y matrices for a spec; centring constants come from `train` only."""
    s = SPECS[name]
    cols = list(s["cols"])
    Xtr = train[cols].astype(float).copy()
    Xte = test[cols].astype(float).copy()
    if s["kind"] == "quadratic":
        c = float(Xtr["rh90_per10h"].mean())
        Xtr["rh90_sq"] = (Xtr["rh90_per10h"] - c) ** 2
        Xte["rh90_sq"] = (Xte["rh90_per10h"] - c) ** 2
    return Xtr, train["y"].values.astype(float), Xte


def fit_predict(name, train, test, cluster=None):
    """Fit a spec on train, return (predictions, fitted object or None, X, names)."""
    Xtr, ytr, Xte = make_xy(name, train, test)
    if SPECS[name]["kind"] == "ridge":
        C = choose_C(Xtr, ytr, train["year"].values)
        sc = StandardScaler().fit(Xtr)
        m = LogisticRegression(C=C, l1_ratio=0.0, solver="lbfgs", max_iter=2000)
        m.fit(sc.transform(Xtr), ytr)
        return m.predict_proba(sc.transform(Xte))[:, 1], (m, sc, C), Xte, list(Xte.columns)
    if len(SPECS[name]["cols"]) == 0:
        p = np.full(len(test), ytr.mean())
        return p, None, Xte, []
    res = fm.fit_logit(Xtr, ytr, cluster=cluster)
    return fm.predict(res, Xte), res, Xte, list(Xte.columns)


def choose_C(X, y, groups, grid=(0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0)):
    """Inner leave-one-year-out AUC to pick the ridge penalty (training data only)."""
    best, bestC = -np.inf, 1.0
    for C in grid:
        aucs = []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            if y[tr].min() == y[tr].max() or y[te].min() == y[te].max():
                continue
            sc = StandardScaler().fit(X[tr])
            m = LogisticRegression(C=C, l1_ratio=0.0, solver="lbfgs", max_iter=2000)
            m.fit(sc.transform(X[tr]), y[tr])
            aucs.append(roc_auc_score(y[te], m.predict_proba(sc.transform(X[te]))[:, 1]))
        if aucs and np.mean(aucs) > best:
            best, bestC = np.mean(aucs), C
    return bestC
