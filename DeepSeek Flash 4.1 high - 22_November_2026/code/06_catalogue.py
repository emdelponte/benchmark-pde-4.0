"""Step 6: catalogue of pre-anthesis (available-by-anthesis) variables."""
import fhb_env  # noqa: F401
import os
import re

import numpy as np
import pandas as pd

import fhb_env as env

pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 400)
pd.set_option("display.max_colwidth", 90)

df = pd.read_pickle(os.path.join(env.OUT, "fhb_raw2.pkl"))
flat = pd.read_csv(os.path.join(env.OUT, "yaml_columns_flat.csv"))
meta = flat.set_index("name")
vm = pd.read_csv(os.path.join(env.DATA, "VariablesMetaData.csv")).set_index("variable_name")

wcols = [c for c in df.columns if c in meta.index]
m = meta.loc[wcols].copy()
m["series"] = [vm.loc[c, "variable_type"] if c in vm.index else None for c in wcols]
m["period_csv"] = [vm.loc[c, "period"] if c in vm.index else None for c in wcols]
m["source"] = [vm.loc[c, "origin"] if c in vm.index else None for c in wcols]
m["unit_csv"] = None

pre = m[m["analysis_period"].isin(["pre", "anthesis", "pre-anthesis"])]
print("pre-anthesis variables:", len(pre))
print("end-day distribution:", pre["window_end_day"].value_counts().sort_index().to_dict())

# ---- family (condition) x window matrix -------------------------------------
pre = pre.copy()
pre["family"] = pre["condition"].fillna("legacy/other")
pre["win"] = pre.apply(lambda r: f"{int(r['window_start_day'])}..{int(r['window_end_day'])}"
                       if pd.notna(r["window_start_day"]) else "NA", axis=1)
pre["step"] = pre["time_step"].fillna("NA") + "/24h"
# 12h vs 24h is in the name suffix; recover it
pre["scope"] = np.where(pre.index.str.endswith("12H"), "12H",
                        np.where(pre.index.str.endswith("24H"), "24H", "na"))

print("\n# families:", pre["family"].nunique())
print(pre.groupby(["family"]).size().sort_values(ascending=False).to_string())

print("\n== families x windows (count) ==")
ct = pd.crosstab(pre["family"], pre["win"])
print(ct.to_string())

print("\n== full catalogue of distinct (family, window, scope) with one example ==")
cat = (pre.groupby(["family", "win", "scope", "time_step", "metric"], dropna=False)
       .agg(n_vars=("description", "size"), example=("description", "first"))
       .reset_index().sort_values(["family", "win"]))
cat.to_csv(os.path.join(env.OUT, "pre_catalogue.csv"), index=False)
print(cat.to_string())

# ---- duplicated / deprecated columns ---------------------------------------
print("\n== columns flagged identical_to (numeric duplicates) ==")
dup = pre[pre["identical_to"].notna()]
print("n flagged:", len(dup))
print(dup[["description", "identical_to", "canonical", "deprecated"]].to_string())
if len(dup):
    for c in dup.index:
        twin = dup.loc[c, "identical_to"]
        if twin in df.columns:
            same = np.allclose(df[c].astype(float), df[twin].astype(float),
                               equal_nan=True)
            print(f"  verify {c} == {twin}: {same}")
