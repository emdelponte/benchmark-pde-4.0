"""Step 14: discrimination structure (within-year vs between-year) and figures."""
import fhb_env  # noqa: F401
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

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
d["state"] = df["state"].astype(str).values
d["trial"] = df["trial"].values
d_cc = d.dropna(subset=["corn"]).reset_index(drop=True)

MODELS = ["M1", "M2", "M4", "M5"]

# ---------------------------------------------------------------- OOF predictions
oofs = {}
folds = {}
for name in MODELS:
    data = d_cc if name == "M4" else d
    y = data["y"].values.astype(float)
    pred = np.full(len(data), np.nan)
    frows = []
    for yr in sorted(data["year"].unique()):
        te = (data["year"] == yr).values
        tr = ~te
        pr, obj, Xte, nm = fs.fit_predict(name, data[tr], data[te],
                                         cluster=data.loc[tr, "wgroup"].values)
        pred[te] = pr
        frows.append({"year": yr, "n": int(te.sum()), "events": int(y[te].sum()),
                      "auc": fm.auc(y[te], pr)})
    oofs[name] = pred
    folds[name] = pd.DataFrame(frows)

p("=" * 100)
p("A. WITHIN-YEAR vs BETWEEN-YEAR DISCRIMINATION (LOYO out-of-fold predictions)")
p("=" * 100)
p("  'within-year' averages AUC computed inside each year that has both classes.")
p("  'between-year' uses the 32 year-level means (mean prediction vs event fraction).")
rows = []
for name in MODELS:
    data = d_cc if name == "M4" else d
    y = data["y"].values.astype(float)
    pr = oofs[name]
    f = folds[name]
    within = f["auc"].dropna()
    yr = pd.DataFrame({"y": y, "p": pr}).groupby(data["year"].values).mean()
    between = roc_auc_score((yr["y"] > 0.5).astype(int), yr["p"]) if yr["y"].nunique() > 1 else np.nan
    rows.append({"model": name, "pooled_auc": fm.auc(y, pr),
                 "within_year_median": within.median(),
                 "within_year_mean": within.mean(),
                 "between_year_auc": between,
                 "n_years_scored": len(within)})
    p(f"  {name}: pooled={fm.auc(y, pr):.3f}  within-year median={within.median():.3f} "
      f"(mean {within.mean():.3f})  between-year={between:.3f}")
pd.DataFrame(rows).to_csv(os.path.join(env.OUT, "within_between_auc.csv"), index=False)

p("\n  per-year detail for M5 (best weather-only) and M4 (agronomic):")
det = folds["M5"].merge(folds["M4"], on="year", suffixes=("_M5", "_M4"))
p(det.round(3).to_string(index=False))

# ---------------------------------------------------------------------- figures
FIG = env.FIG
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3})

# 1. outcome distribution
fig, ax = plt.subplots(1, 2, figsize=(9, 3.2))
ax[0].hist(df["S"], bins=np.arange(0, 90, 2.5), color="#4477AA")
ax[0].axvline(5, color="crimson", ls="--", lw=1)
ax[0].set_xlabel("FHB index S (%)")
ax[0].set_ylabel("plots")
ax[0].set_title("A  FHB index distribution (n=999)")
ax[1].ecdf = None
xs = np.sort(df["S"])
ax[1].step(xs, np.arange(1, len(xs) + 1) / len(xs))
ax[1].axvline(5, color="crimson", ls="--", lw=1)
ax[1].set_xlabel("FHB index S (%)")
ax[1].set_ylabel("cumulative fraction")
ax[1].set_title("B  ECDF; 39.5% of plots at S >= 5%")
ax[1].set_xlim(0, 90)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig1_outcome.png"))
plt.close(fig)

# 2. ROC curves
fig, ax = plt.subplots(figsize=(4.2, 4.0))
for name in MODELS:
    data = d_cc if name == "M4" else d
    y = data["y"].values
    fpr, tpr, _ = roc_curve(y, oofs[name])
    ax.plot(fpr, tpr, lw=1.6,
            label=f"{name} (AUC {roc_auc_score(y, oofs[name]):.3f})")
ax.plot([0, 1], [0, 1], "k:", lw=1)
ax.set_xlabel("1 - specificity")
ax.set_ylabel("sensitivity")
ax.set_title("Leave-one-year-out ROC")
ax.legend(loc="lower right", fontsize=7, frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig2_roc.png"))
plt.close(fig)

# 3. calibration (deciles) for M2, M5, M4
def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    ph = k / n
    d_ = 1 + z ** 2 / n
    c = (ph + z ** 2 / (2 * n)) / d_
    h = z * np.sqrt(ph * (1 - ph) / n + z ** 2 / (4 * n ** 2)) / d_
    return c - h, c + h


fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
for axi, name in zip(axes, ["M2", "M5", "M4"]):
    data = d_cc if name == "M4" else d
    y = data["y"].values.astype(float)
    pr = oofs[name]
    q = pd.qcut(pd.Series(pr), 10, duplicates="drop")
    g = pd.DataFrame({"y": y, "p": pr, "q": q}).groupby("q", observed=True).agg(
        n=("y", "size"), obs=("y", "mean"), pred=("p", "mean"))
    g["lo"], g["hi"] = zip(*[wilson(o * n_, n_) for o, n_ in zip(g["obs"], g["n"])])
    axi.errorbar(g["pred"], g["obs"],
                 yerr=[g["obs"] - g["lo"], g["hi"] - g["obs"]],
                 fmt="o", ms=4, capsize=2, color="#CC6677")
    axi.plot([0, 1], [0, 1], "k:", lw=1)
    axi.set_xlim(0, 0.85)
    axi.set_ylim(0, 0.85)
    axi.set_xlabel("predicted probability")
    axi.set_title(f"{name}")
    axi.text(0.04, 0.9, f"slope={fm.calib(y, pr)[1]:.2f}\nint={fm.calib(y, pr)[0]:+.2f}",
             transform=axi.transAxes, fontsize=7, va="top")
axes[0].set_ylabel("observed event fraction")
fig.suptitle("Leave-one-year-out calibration (deciles, 95% Wilson CI)", y=1.02, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig3_calibration.png"), bbox_inches="tight")
plt.close(fig)

# 4. per-year AUC dot plot
fig, ax = plt.subplots(figsize=(6.4, 3.4))
years = sorted(df["year"].unique())
ax.plot(years, folds["M5"].set_index("year").reindex(years)["auc"], "o", ms=4,
        label="M5 (weather only)")
ax.plot(years, folds["M4"].set_index("year").reindex(years)["auc"], "s", ms=4,
        label="M4 (weather + agronomy)")
ax.axhline(0.5, color="k", ls=":", lw=1)
ax.set_xlabel("held-out year")
ax.set_ylabel("AUC within held-out year")
ax.set_title("Year-to-year variability of discrimination")
ax.legend(frameon=False, fontsize=7)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig4_fold_auc.png"))
plt.close(fig)

# 5. complexity vs OOF AUC (LOYO)
cv = pd.read_csv(os.path.join(env.OUT, "cv_summary.csv"))
loyo = cv[cv["scheme"] == "LOYO"]
fig, ax = plt.subplots(figsize=(4.6, 3.2))
for _, r in loyo.iterrows():
    ax.errorbar(r["n_params"], r["oof_auc"],
                yerr=[[r["oof_auc"] - r["auc_lo"]], [r["auc_hi"] - r["oof_auc"]]],
                fmt="o", ms=5, capsize=3)
    ax.annotate(r["model"], (r["n_params"], r["oof_auc"]),
                textcoords="offset points", xytext=(5, -8), fontsize=7)
ax.axhline(0.5, color="k", ls=":", lw=1)
ax.set_xlabel("estimated non-intercept parameters")
ax.set_ylabel("pooled out-of-fold AUC")
ax.set_title("Complexity vs LOYO discrimination")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "fig5_complexity.png"))
plt.close(fig)

p("\nfigures written to outputs/figures/")
for f in sorted(os.listdir(FIG)):
    p("  ", f, os.path.getsize(os.path.join(FIG, f)), "bytes")

with open(os.path.join(env.OUT, "14_figures.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/14_figures.txt")
