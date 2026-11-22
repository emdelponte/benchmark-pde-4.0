"""Step 11: grouped cross-validation of the pre-specified models.

Schemes
  LOYO  leave-one-year-out (32 folds)         -- temporal transportability (primary)
  LOSO  leave-one-state-out (17 folds)        -- spatial transportability
  K5    five chronological blocks of years    -- lower-variance check

Everything (centring, standardisation, ridge penalty) is fitted inside training folds.
Pooled out-of-fold (OOF) predictions are used for AUC/Brier/calibration; per-fold metrics
are reported with their denominators and are never averaged as if exchangeable.
"""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd

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
d_all = d.copy()
d_cc = d.dropna(subset=["corn"]).copy()  # for M4

NBOOT = 1000


def run_scheme(scheme, data, model_names):
    """Return dict model -> (oof, folds_df)."""
    res = {}
    if scheme in ("LOYO", "LOSO"):
        gcol = "year" if scheme == "LOYO" else "state"
        groups = sorted(data[gcol].unique())
        fold_list = [(g,) for g in groups]
    elif scheme == "K5":
        years = sorted(data["year"].unique())
        blocks = np.array_split(np.array(years), 5)
        fold_list = [tuple(b) for b in blocks]
        gcol = "year"
    for name in model_names:
        oof = np.full(len(data), np.nan)
        rows = []
        for fold in fold_list:
            te = data[gcol].isin(fold).values
            tr = ~te
            if data["y"].values[tr].min() == data["y"].values[tr].max():
                rows.append({"fold": str(fold), "n_test": int(te.sum()),
                             "events_test": int(data["y"].values[te].sum()),
                             "auc": np.nan, "brier": np.nan, "note": "no variation in train"})
                continue
            pr, obj, Xte, names = fs.fit_predict(name, data[tr], data[te],
                                                 cluster=data.loc[tr, "wgroup"].values)
            oof[te] = pr
            rows.append({"fold": str(fold), "n_test": int(te.sum()),
                         "events_test": int(data["y"].values[te].sum()),
                         "auc": fm.auc(data["y"].values[te], pr),
                         "brier": fm.brier(data["y"].values[te], pr),
                         "mean_pred": float(np.mean(pr)),
                         "note": ""})
        res[name] = (oof, pd.DataFrame(rows))
    return res


MODELS_ALL = ["M0", "M1", "M2", "M3", "M5", "M6", "M7"]
MODELS_CC = MODELS_ALL + ["M4"]

summary = []
fold_tables = []
for scheme in ("LOYO", "LOSO", "K5"):
    p("\n" + "=" * 100)
    p(f"SCHEME {scheme}")
    p("=" * 100)
    r_all = run_scheme(scheme, d_all, MODELS_ALL)
    r_cc = run_scheme(scheme, d_cc, ["M4"])
    r = {**r_all, "M4": r_cc["M4"]}
    for name in ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]:
        oof, folds = r[name]
        data = d_cc if name == "M4" else d_all
        ok = ~np.isnan(oof)
        y = data["y"].values[ok]
        pr = oof[ok]
        a = fm.auc(y, pr)
        b = fm.brier(y, pr)
        ci, sl, cis, sls = fm.calib(y, pr)
        lo, hi, nb = fm.cluster_bootstrap_metric(y, pr, data["wgroup"].values[ok],
                                                 metric="auc", n_boot=NBOOT)
        blo, bhi, _ = fm.cluster_bootstrap_metric(y, pr, data["wgroup"].values[ok],
                                                  metric="brier", n_boot=NBOOT)
        folds = folds.assign(model=name, scheme=scheme)
        fold_tables.append(folds)
        nf = folds["auc"].dropna()
        summary.append({
            "scheme": scheme, "model": name, "n": int(ok.sum()),
            "events": int(y.sum()), "n_params": len(fs.SPECS[name]["cols"]),
            "oof_auc": a, "auc_lo": lo, "auc_hi": hi,
            "oof_brier": b, "brier_lo": blo, "brier_hi": bhi,
            "calib_intercept": ci, "calib_slope": sl,
            "n_folds_scored": int(len(nf)),
            "fold_auc_median": float(nf.median()) if len(nf) else np.nan,
            "fold_auc_p10": float(nf.quantile(.1)) if len(nf) else np.nan,
            "fold_auc_p90": float(nf.quantile(.9)) if len(nf) else np.nan,
            "fold_auc_min": float(nf.min()) if len(nf) else np.nan,
            "fold_auc_max": float(nf.max()) if len(nf) else np.nan,
        })
        p(f"{name}: OOF AUC={a:.3f} [{lo:.3f},{hi:.3f}]  Brier={b:.3f} "
          f"[{blo:.3f},{bhi:.3f}]  calib int={ci:+.3f} slope={sl:.3f}  "
          f"folds scored={len(nf)}/{len(folds)}  fold AUC median={np.nanmedian(nf) if len(nf) else np.nan:.3f}")

summ = pd.DataFrame(summary)
summ.to_csv(os.path.join(env.OUT, "cv_summary.csv"), index=False)
folds_all = pd.concat(fold_tables, ignore_index=True)
folds_all.to_csv(os.path.join(env.OUT, "cv_folds.csv"), index=False)

p("\n" + "=" * 100)
p("POOLED SUMMARY (sorted by scheme, then AUC)")
p("=" * 100)
p(summ[["scheme", "model", "n_params", "events", "oof_auc", "auc_lo", "auc_hi",
        "oof_brier", "calib_intercept", "calib_slope", "n_folds_scored",
        "fold_auc_median", "fold_auc_p10", "fold_auc_p90"]].round(3).to_string(index=False))

p("\n" + "=" * 100)
p("OPTIMISM GAP (apparent - OOF AUC, LOYO)")
p("=" * 100)
app = pd.read_csv(os.path.join(env.OUT, "apparent_performance.csv"))
loyo = summ[summ["scheme"] == "LOYO"].set_index("model")
gap = pd.DataFrame({
    "apparent_auc": app.set_index("model")["apparent_auc"],
    "oof_auc_loyo": loyo["oof_auc"],
})
gap["optimism"] = gap["apparent_auc"] - gap["oof_auc_loyo"]
gap["apparent_brier"] = app.set_index("model")["apparent_brier"]
gap["oof_brier_loyo"] = loyo["oof_brier"]
p(gap.round(3).to_string())
gap.to_csv(os.path.join(env.OUT, "optimism_gap.csv"))

p("\n" + "=" * 100)
p("FOLD-LEVEL FRAGILITY (LOYO)")
p("=" * 100)
fl = folds_all[(folds_all["scheme"] == "LOYO") & (folds_all["model"] == "M2")]
p("M2 LOYO folds with a scorable AUC:", int(fl["auc"].notna().sum()), "of", len(fl))
p("folds with <5 test events:", int((fl["events_test"] < 5).sum()))
p(fl.sort_values("auc").head(6).round(3).to_string(index=False))
p("...")
p(fl.sort_values("auc").tail(6).round(3).to_string(index=False))

p("\n" + "=" * 100)
p("LOSO DETAIL (M2 and M4)")
p("=" * 100)
for m in ("M2", "M4"):
    t = folds_all[(folds_all["scheme"] == "LOSO") & (folds_all["model"] == m)]
    p(f"\n{m}:")
    p(t.sort_values("auc").round(3).to_string(index=False))

with open(os.path.join(env.OUT, "11_validate.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/11_validate.txt")
