"""Shared modelling utilities for the FHB analysis (logistic regression,
grouped cross-validation, calibration, bootstrap).

Only pre-anthesis (window_end_day <= 0) variables are ever used; the column
lookup is restricted to the YAML `pre` period.
"""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.metrics import brier_score_loss, roc_auc_score

import fhb_env as env

DESIGN = ["id", "year", "state", "fdate", "type", "resist", "corn", "S"]


# --------------------------------------------------------------------------- data
def load():
    df = pd.read_pickle(os.path.join(env.OUT, "fhb_raw2.pkl"))
    flat = pd.read_csv(os.path.join(env.OUT, "yaml_columns_flat.csv")).set_index("name")
    wcols = [c for c in df.columns if c not in DESIGN and c != "envkey"]
    df["wgroup"] = pd.util.hash_pandas_object(
        df[wcols].astype(float).round(6), index=False).astype("int64")
    df["trial"] = (df["state"].astype(str) + "|" + df["year"].astype(str) + "|" +
                   df["fdate"].dt.strftime("%m-%d"))
    df["resist_ord"] = df["resist"].map({"VS": 0, "S": 1, "MS": 2, "MR": 3}).astype(float)
    return df, flat


def find_var(flat, desc_regex, ws, we):
    """Unique pre-anthesis column matching a description and a signed window."""
    m = flat[(flat["window_start_day"] == ws) & (flat["window_end_day"] == we)]
    m = m[m["description"].str.contains(desc_regex, case=False, regex=True, na=False)]
    assert len(m) == 1, f"expected 1 match for {desc_regex} [{ws},{we}], got {list(m.index)}"
    return m.index[0]


PAT = {
    "rh90_h": r"^No\. hr \(RH >= 90%\)",
    "rh80_h": r"^No\. hr \(RH >= 80%\)",
    "t30_h": r"^No\. hr \(T > 30degC\)",
    "t15_30_h": r"^No\. hr \(15degC <= T <= 30degC\)$",
    "ww1590_h": r"^No\. hr \(15degC <= T <= 30degC & RH >= 90%\)",
    "ww980_h": r"^No\. hr \(9degC <= T <= 30degC & RH >= 80%\)",
    "meanT": r"^Mean daily T \(degC\)",
    "meanRH": r"^Mean daily RH \(%\)",
    "meanVPD": r"^Mean daily VPD \(kPa\)",
    "meanTDD": r"^Mean daily TDD \(degC\)",
    "meanD": r"^Mean daily D \(degC\)",
}


def vars_for_window(flat, ws, we):
    """All pre-anthesis candidates available for a signed window."""
    out = {}
    for k, pat in PAT.items():
        try:
            out[k] = find_var(flat, pat, ws, we)
        except AssertionError:
            out[k] = None
    return out


# ------------------------------------------------------------------------ models
def fit_logit(X, y, cluster=None):
    """MLE logistic regression. X may already contain a constant column."""
    Xc = sm.add_constant(np.asarray(X, dtype=float), has_constant="add")
    kw = {}
    if cluster is not None:
        kw = dict(cov_type="cluster", cov_kwds={"groups": np.asarray(cluster)})
    res = sm.Logit(np.asarray(y, dtype=float), Xc).fit(disp=0, maxiter=200, **kw)
    return res


def predict(res, X):
    Xc = sm.add_constant(np.asarray(X, dtype=float), has_constant="add")
    return res.predict(Xc)


# ----------------------------------------------------------------------- metrics
def auc(y, p):
    y = np.asarray(y)
    if y.min() == y.max():
        return np.nan
    return roc_auc_score(y, p)


def brier(y, p):
    return brier_score_loss(np.asarray(y), np.asarray(p))


def calib(y, p):
    """Calibration intercept and slope from y ~ logit(p)."""
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / (1 - np.clip(p, 1e-6, 1 - 1e-6)))
    X = sm.add_constant(lp)
    try:
        r = sm.Logit(np.asarray(y, dtype=float), X).fit(disp=0, maxiter=100)
        return float(r.params[0]), float(r.params[1]), float(r.bse[0]), float(r.bse[1])
    except Exception:  # noqa: BLE001
        return np.nan, np.nan, np.nan, np.nan


def cluster_bootstrap_metric(y, p, groups, metric="auc", n_boot=2000, seed=20240101):
    """Percentile CI resampling whole clusters (weather groups)."""
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    p = np.asarray(p)
    g = np.asarray(groups)
    uniq = np.unique(g)
    idx_by_g = {u: np.where(g == u)[0] for u in uniq}
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx_by_g[u] for u in pick])
        yy, pp = y[rows], p[rows]
        if yy.min() == yy.max():
            continue
        vals.append(auc(yy, pp) if metric == "auc" else brier(yy, pp))
    vals = np.array(vals)
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), len(vals)


# ------------------------------------------------------------------- validation
def grouped_cv(df, model_spec, group_col, y_col="EPI", fit_kwargs=None):
    """Leave-one-group-out (or k-fold) CV with all estimation inside the fold.

    model_spec: callable(df_train) -> (X_train, y_train, X_test) using only
    training-derived quantities. Returns (oof predictions, fold summary rows).
    """
    fit_kwargs = fit_kwargs or {}
    y = df[y_col].values.astype(float)
    oof = np.full(len(df), np.nan)
    rows = []
    for g in sorted(df[group_col].unique()):
        te = (df[group_col] == g).values
        tr = ~te
        Xtr, ytr, Xte = model_spec(df[tr], df[te])
        try:
            res = fit_logit(Xtr, ytr, **(fit_kwargs if fit_kwargs else {}))
            p = predict(res, Xte)
            oof[te] = p
            rows.append({"group": g, "n_train": int(tr.sum()), "n_test": int(te.sum()),
                         "events_test": int(y[te].sum()),
                         "auc": auc(y[te], p), "brier": brier(y[te], p),
                         "mean_pred": float(np.mean(p))})
        except Exception as e:  # noqa: BLE001
            rows.append({"group": g, "n_train": int(tr.sum()), "n_test": int(te.sum()),
                         "events_test": int(y[te].sum()), "auc": np.nan,
                         "brier": np.nan, "mean_pred": np.nan, "error": str(e)[:80]})
    return oof, pd.DataFrame(rows)


def kfold_groups(df, group_col, k=5, y_col="EPI", model_fn=None, seed=7):
    """k-fold CV where folds are blocks of whole groups (sorted chronologically
    when the group is the year)."""
    groups = sorted(df[group_col].unique())
    folds = np.array_split(np.array(groups), k)
    y = df[y_col].values.astype(float)
    oof = np.full(len(df), np.nan)
    rows = []
    for i, fold in enumerate(folds):
        te = df[group_col].isin(fold).values
        tr = ~te
        Xtr, ytr, Xte = model_fn(df[tr], df[te])
        res = fit_logit(Xtr, ytr)
        p = predict(res, Xte)
        oof[te] = p
        rows.append({"fold": i, "groups": f"{fold[0]}-{fold[-1]}",
                     "n_train": int(tr.sum()), "n_test": int(te.sum()),
                     "events_test": int(y[te].sum()), "auc": auc(y[te], p),
                     "brier": brier(y[te], p)})
    return oof, pd.DataFrame(rows)


def or_table(res, names, cluster_label=None):
    """Odds ratios with 95% CI from a fitted statsmodels result."""
    ci = np.asarray(res.conf_int(alpha=0.05), dtype=float)
    out = pd.DataFrame({
        "term": ["Intercept"] + list(names),
        "coef": np.asarray(res.params, dtype=float),
        "se": np.asarray(res.bse, dtype=float),
        "z": np.asarray(res.tvalues, dtype=float),
        "p": np.asarray(res.pvalues, dtype=float),
        "OR": np.exp(np.asarray(res.params, dtype=float)),
        "OR_lo": np.exp(ci[:, 0]),
        "OR_hi": np.exp(ci[:, 1]),
    })
    out.attrs["cluster"] = cluster_label
    return out
