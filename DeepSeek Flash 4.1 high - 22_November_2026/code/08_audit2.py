"""Step 8: second audit pass -- temporal/spatial structure, clustering, event
counts at environment level, and consistency checks used in the audit report."""
import fhb_env  # noqa: F401
import os

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

import fhb_env as env

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 300)
out = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


df = pd.read_pickle(os.path.join(env.OUT, "fhb_raw2.pkl"))
df["envkey"] = (df["state"].astype(str) + "|" + df["year"].astype(str) + "|" +
                df["fdate"].dt.strftime("%m-%d"))
y5 = (df["S"] >= 5).astype(int)

p("=" * 100)
p("A. TIME STAMPS")
p("=" * 100)
p("fdate time-of-day values:", df["fdate"].dt.strftime("%H:%M:%S").unique())
p("fdate month distribution:")
p(df["fdate"].dt.month.value_counts().sort_index().to_string())

p("\n" + "=" * 100)
p("B. ENVIRONMENT-LEVEL STRUCTURE")
p("=" * 100)
g = df.groupby("envkey")
tab = pd.DataFrame({
    "n_plots": g.size(),
    "n_y5": g.apply(lambda d: int((d["S"] >= 5).sum()), include_groups=False),
    "meanS": g["S"].mean(),
})
p("environments:", len(tab))
p("environments with >=1 case (S>=5%):", int((tab["n_y5"] > 0).sum()))
p("environments with 0 cases:", int((tab["n_y5"] == 0).sum()))
p("environments all-case:", int((tab["n_y5"] == tab["n_plots"]).sum()))
p("distribution of cases per environment:")
p(tab["n_y5"].value_counts().sort_index().to_string())
p("\nplots per environment:", tab["n_plots"].describe().to_dict())

p("\nstate-year cells (regardless of anthesis date):")
sy = df.groupby(["state", "year"]).size().reset_index(name="n")
p("n state-year cells:", len(sy), " cells with 1 plot:", int((sy["n"] == 1).sum()))
p("state-year cells with >=1 case:",
  int(df.assign(y5=y5).groupby(["state", "year"])["y5"].max().sum()), "of", len(sy))

p("\nyears represented per state:")
p(df.groupby("state")["year"].agg(["nunique", "min", "max"]).to_string())
p("\nnumber of states per year:")
p(df.groupby("year")["state"].nunique().to_string())

p("\n" + "=" * 100)
p("C. WEATHER-VECTOR SHARING (design dependence)")
p("=" * 100)
DESIGN = {"id", "year", "state", "fdate", "type", "resist", "corn", "S", "envkey"}
wcols = [c for c in df.columns if c not in DESIGN]
vec = df[wcols].astype(float).round(6).astype(str).agg("|".join, axis=1)
df["vec"] = vec
p("distinct weather vectors:", df["vec"].nunique())
vtab = df.groupby("vec").agg(n=("id", "size"), n_state=("state", "nunique"),
                             n_year=("year", "nunique"), n_env=("envkey", "nunique"))
p("\nplots per weather vector:", vtab["n"].describe().to_dict())
p("vectors spanning >1 state:", int((vtab["n_state"] > 1).sum()),
  " >1 year:", int((vtab["n_year"] > 1).sum()),
  " >1 environment:", int((vtab["n_env"] > 1).sum()))
p("max plots sharing one vector:", int(vtab["n"].max()))
p("plots in a shared vector (n>1):", int(vtab.loc[vtab['n'] > 1, 'n'].sum()))

p("\n" + "=" * 100)
p("D. UNIVARIATE DISCRIMINATION (descriptive, not model selection)")
p("=" * 100)
cands = {
    "mean RH 20d pre (RH.A.1)": "RH.A.1",
    "mean RH 7d pre (RH7)": "RH7",
    "mean RH 7d pre 24H (RH.A.PRE7... not avail)": None,
    "hours RH>=90 7d pre (RH907)": "RH907",
    "hours RH>=90 20d pre (RH.G90.CHD.1)": "RH.G90.CHD.1",
    "warm-wet hours 15-30&RH80 7d (TRH807)": "TRH807",
    "warm-wet hours 9-30&RH80 7d (TRH.9T30nRHG80.PRE7.24H)":
        "TRH.9T30nRHG80.PRE7.24H",
    "mean T 7d pre (T.A.PRE7.24H)": "T.A.PRE7.24H",
    "hours T>30 7d pre (T.G30.PRE7.24H)": "T.G30.PRE7.24H",
    "mean VPD 10d pre (VPD.A.1)": "VPD.A.1",
    "mean TDD 20d pre (TDD.A.1)": "TDD.A.1",
    "corn residue": "corn",
    "resistance (ordinal VS<S<MS<MR)": "resist",
}
rows = []
for lab, col in cands.items():
    if col is None:
        continue
    if col == "resist":
        x = df["resist"].map({"VS": 0, "S": 1, "MS": 2, "MR": 3}).astype(float)
    else:
        x = df[col].astype(float)
    ok = x.notna().values
    auc = roc_auc_score(y5[ok], x[ok])
    rows.append({"predictor": lab, "var": col, "auc_plot_level": auc,
                 "auc_direction": "higher=more risk" if auc >= .5 else "higher=less risk"})
u = pd.DataFrame(rows).sort_values("auc_plot_level", ascending=False)
p(u.round(3).to_string(index=False))
u.to_csv(os.path.join(env.OUT, "univariate_auc.csv"), index=False)

p("\n" + "=" * 100)
p("E. WITHIN-ENVIRONMENT OUTCOME VARIABILITY")
p("=" * 100)
p("share of total S variance that is between environments:")
p(f"  {(df.groupby('envkey')['S'].transform('mean').var() / df['S'].var()):.3f}")
p("correlation of S with environment-mean S (plot level):",
  round(df["S"].corr(df.groupby("envkey")["S"].transform("mean")), 3))
p("\nS by resistance class, within environments that contain >1 class:")
multi = df.groupby("envkey")["resist"].nunique()
sub = df[df["envkey"].isin(multi[multi > 1].index)]
p(sub.groupby("resist", observed=True)["S"].agg(["size", "mean", "median"]).round(2).to_string())

p("\n" + "=" * 100)
p("F. INTERNAL CONSISTENCY OF DERIVED COUNTS")
p("=" * 100)
chk = [("T157", "T.L15.PRE7.24H", 7 * 24),
       ("T.A.PRE7.24H", None, None)]
a = df["T157"].astype(float) + df["T.L15.PRE7.24H"].astype(float)
p("hours T>=15 + hours T<15 in 7 d (should equal 168):",
  "min", a.min(), "max", a.max())
b = df["T.G30.PRE5.24H"].astype(float)
p("hours T>30 in 5 d: max", b.max(), "(theoretical 120)")
p("RH>=90 hours 7d max:", df["RH907"].max(), "(theoretical 168)")
p("RH.A.1 range:", df["RH.A.1"].min(), df["RH.A.1"].max())
p("pressure mean range:", df["RH.A.1"].min(), "(hPa check separately)")
p("P.A.1:", df["P.A.1"].min(), df["P.A.1"].max())
p("VPD.A.1:", df["VPD.A.1"].min(), df["VPD.A.1"].max())
p("mean over 7d of RH vs RH>=90 hours Spearman:",
  round(df["RH7"].corr(df["RH907"], method="spearman"), 3))

with open(os.path.join(env.OUT, "audit_stats2.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
p("\nwrote outputs/audit_stats2.txt")
