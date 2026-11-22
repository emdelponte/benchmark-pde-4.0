"""Step 5: structural + exploratory audit of FHBVer2.

Writes machine-readable summaries to outputs/ and a human-readable audit to
outputs/audit_stats.txt. No modelling here.
"""
import fhb_env  # noqa: F401
import json
import os
import sys

import numpy as np
import pandas as pd

import fhb_env as env

pd.set_option("display.width", 220)
pd.set_option("display.max_rows", 200)

out = []


def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


df = pd.read_pickle(os.path.join(env.OUT, "fhb_raw.pkl"))
p("=" * 100)
p("1. DIMENSIONS AND UNIT OF OBSERVATION")
p("=" * 100)
p("rows x cols:", df.shape)
p("\nhead of design columns:")
p(df[["id", "year", "state", "fdate", "type", "resist", "corn", "S"]].head(12).to_string())
p("\ndate range:", df["fdate"].min(), "->", df["fdate"].max())
p("years:", sorted(df["year"].unique()))
p("n years:", df["year"].nunique(), " n states:", df["state"].nunique())
p("\nrows per year:")
p(df["year"].value_counts().sort_index().to_string())
p("\nrows per state:")
p(df["state"].value_counts().to_string())
p("\ncross-tab state x wheat type:")
p(pd.crosstab(df["state"], df["type"]).to_string())
p("\nresist levels:", df["resist"].value_counts(dropna=False).to_dict())
p("type levels:", df["type"].value_counts(dropna=False).to_dict())
p("corn levels:", df["corn"].value_counts(dropna=False).to_dict())

p("\n-- grouping structure --")
for keys in (["state", "year"], ["state", "year", "fdate"],
             ["state", "year", "fdate", "type"],
             ["state", "year", "fdate", "resist"],
             ["state", "year", "fdate", "type", "resist", "corn"]):
    g = df.groupby(keys, dropna=False).size()
    p(f"unique {'+'.join(keys)}: {len(g)}  (median rows/group {g.median():.0f}, "
      f"max {g.max()}, singleton groups {(g == 1).sum()})")

p("\n-- exact duplicate rows (all 337 cols) --")
p("n duplicate rows:", int(df.duplicated().sum()))

p("\n" + "=" * 100)
p("2. RESPONSE VARIABLE S (FHB index, %)")
p("=" * 100)
s = df["S"]
p(s.describe(percentiles=[.01, .05, .1, .25, .5, .75, .9, .95, .99]).to_string())
p("\nzeros:", int((s == 0).sum()), f"({(s == 0).mean()*100:.1f}%)")
p("S < 0 or > 100:", int(((s < 0) | (s > 100)).sum()))
p("\nS distribution by year (median, mean, n, ninf>=5%):")
tab = df.groupby("year").agg(n=("S", "size"), median=("S", "median"),
                             mean=("S", "mean"), q90=("S", lambda x: x.quantile(.9)),
                             pct_ge5=("S", lambda x: (x >= 5).mean() * 100))
p(tab.round(2).to_string())
p("\nS distribution by state:")
tab2 = df.groupby("state").agg(n=("S", "size"), median=("S", "median"),
                               mean=("S", "mean"),
                               pct_ge5=("S", lambda x: (x >= 5).mean() * 100))
p(tab2.round(2).to_string())
p("\nS by wheat type:")
p(df.groupby("type")["S"].describe().round(2).to_string())
p("\nS by resistance class:")
p(df.groupby("resist", observed=True)["S"].describe().round(2).to_string())
p("\nS by corn residue:")
p(df.groupby("corn", dropna=False)["S"].describe().round(2).to_string())

p("\n-- candidate binary outcome thresholds --")
rows = []
for thr in (0, 1, 2, 5, 10, 15, 20, 25, 30):
    y = (s > thr).astype(int)
    rows.append({"threshold_pct": thr, "events": int(y.sum()),
                 "nonevents": int((1 - y).sum()),
                 "prevalence": round(y.mean(), 4)})
thr_tab = pd.DataFrame(rows)
thr_tab.to_csv(os.path.join(env.OUT, "threshold_prevalence.csv"), index=False)
p(thr_tab.to_string())

p("\n" + "=" * 100)
p("3. MISSINGNESS AND DATA-QUALITY CHECKS")
p("=" * 100)
na = df.isna().sum()
p("columns with any NA:", int((na > 0).sum()))
p(na[na > 0].to_string() if (na > 0).any() else "none")
p("\nconstant columns:", [c for c in df.columns if df[c].nunique(dropna=False) <= 1])

# valid-range checks from the YAML
flat = pd.read_csv(os.path.join(env.OUT, "yaml_columns_flat.csv"))
viol = []
for _, r in flat.iterrows():
    nm = r["name"]
    if nm not in df.columns or pd.isna(r.get("valid_range")):
        continue
    vr = json.loads(r["valid_range"])
    lo, hi = vr.get("min"), vr.get("max")
    x = df[nm]
    nb = int(((x < lo) | (x > hi)).sum()) if x.dtype.kind in "if" else 0
    if nb:
        viol.append((nm, lo, hi, nb, float(x.min()), float(x.max())))
p("\ncolumns violating documented valid_range:", len(viol))
for v in viol[:40]:
    p("  ", v)

p("\n" + "=" * 100)
p("4. CLUSTERING / EFFECTIVE SAMPLE SIZE")
p("=" * 100)
envkey = df["state"].astype(str) + "_" + df["year"].astype(str) + "_" + \
    df["fdate"].dt.strftime("%Y-%m-%d")
df["envkey"] = envkey
p("unique state-year-anthesis-date environments:", envkey.nunique())
sz = envkey.value_counts()
p("plots per environment: median", sz.median(), "max", sz.max(),
  "environments with 1 plot:", int((sz == 1).sum()))
p("\nhow many distinct weather vectors? (rows with identical weather block):")
wcols = [c for c in df.columns if c not in
         ("id", "year", "state", "fdate", "type", "resist", "corn", "S", "envkey")]
p("n weather columns:", len(wcols))
wx = df[wcols].astype(float).round(6)
p("n unique weather vectors:", wx.drop_duplicates().shape[0])

# outcome clustering within environment
p("\nICC-style check: variance of S between vs within environment groups")
g = df.groupby("envkey")["S"]
grand = df["S"].mean()
between = ((g.mean() - grand) ** 2 * g.size()).sum() / (len(g) - 1)
within = ((df["S"] - g.transform("mean")) ** 2).sum() / (len(df) - len(g))
k = len(df) / len(g)
p(f"between-group MS={between:.2f}, within-group MS={within:.2f}, "
  f"approx ICC={(between - within) / (between + (k - 1) * within):.3f}")

p("\n" + "=" * 100)
p("5. WEATHER PREDICTOR STRUCTURE")
p("=" * 100)
# assign metadata
meta = flat.set_index("name")
meta = meta[meta.index.isin(df.columns)]
p("weather vars with analysis_period pre or end day <=0:",
  int(((meta["analysis_period"].isin(["pre", "anthesis"]))).sum()))
p("\nanalysis_period counts (for weather vars in data):")
p(meta["analysis_period"].value_counts(dropna=False).to_string())
p("\nwindow_end_day value counts:")
p(meta["window_end_day"].value_counts(dropna=False).sort_index().to_string())
p("\nwindow_start_day value counts:")
p(meta["window_start_day"].value_counts(dropna=False).sort_index().to_string())
p("\n[metadata gaps] weather columns missing window bounds in YAML:",
  int(meta["window_end_day"].isna().sum()))
p("  ", meta.index[meta["window_end_day"].isna()].tolist())
p("  YAML fields NOT carried into the flattened dictionary:",
  sorted(set(pd.read_csv(os.path.join(env.DATA, "VariablesMetaData.csv")).columns) -
         set(flat.columns)))

vm = pd.read_csv(os.path.join(env.DATA, "VariablesMetaData.csv")).set_index("variable_name")
both = meta.join(vm[["day", "time_step", "metric", "win_start_day", "win_end_day"]],
                 how="left", rsuffix="_csv")
p("\ntime_step / day combos (from VariablesMetaData.csv):")
p(both.groupby(["time_step_csv", "day"], dropna=False).size().to_string())
p("\nmetric counts (YAML vs CSV):")
p(pd.concat([meta["metric"].value_counts(dropna=False).rename("yaml"),
             both["metric_csv"].value_counts(dropna=False).rename("csv")],
            axis=1).fillna(0).astype(int).to_string())
p("\ndisagreements in window bounds between YAML and CSV:")
mm = both[both["window_end_day"].notna() & both["win_end_day"].notna() &
          (both["window_end_day"] != both["win_end_day"])]
p(mm[["window_start_day", "win_start_day", "window_end_day", "win_end_day"]].to_string()
  if len(mm) else "  none")

p("\n-- extreme-value / sentinel screening on weather vars --")
desc = df[wcols].describe().T
desc["n_zero"] = (df[wcols] == 0).sum()
desc["n_neg"] = (df[wcols] < 0).sum()
extreme = desc[(desc["n_zero"] > 0.8 * len(df)) | (desc["std"] == 0)]
p("near-constant / all-zero columns:", len(extreme))
p(extreme.round(3).to_string() if len(extreme) else "none")

with open(os.path.join(env.OUT, "audit_stats.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
df.to_pickle(os.path.join(env.OUT, "fhb_raw2.pkl"))
p("\nwrote outputs/audit_stats.txt")
