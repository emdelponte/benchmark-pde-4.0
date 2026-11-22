"""Step 3: flatten the YAML dictionary into a per-column table; search for
documented epidemic/binary outcome definitions."""
import fhb_env  # noqa: F401
import json
import os
import re

import pandas as pd
import yaml

import fhb_env as env

with open(os.path.join(env.DATA, "FHBVer2DataDict.yaml"), encoding="utf-8") as fh:
    y = yaml.safe_load(fh)
cols = y["tables"][0]["columns"]

rows = []
for c in cols:
    d = {k: v for k, v in c.items()
         if k not in ("same_condition_as", "same_window_as", "levels")}
    for k in ("range", "valid_range", "value_labels"):
        if k in d:
            d[k] = json.dumps(d[k])
    rows.append(d)
flat = pd.DataFrame(rows)
flat.to_csv(os.path.join(env.OUT, "yaml_columns_flat.csv"), index=False)
print("flattened:", flat.shape)
print("\ncolumns of flattened table:", flat.columns.tolist())
print("\ncategory counts:")
print(flat["category"].value_counts(dropna=False))
print("\nnon weather_derived rows (full):")
print(flat[flat["category"] != "weather_derived"].to_string())

# search textual fields for epidemic / binary / threshold language
pat = re.compile(r"epidemic|binary|threshold|outbreak|binary outcome|class",
                 re.IGNORECASE)
print("\n== YAML text hits for epidemic/binary/threshold ==")
for c in cols:
    txt = json.dumps(c, ensure_ascii=False)
    hits = set(m.group(0).lower() for m in pat.finditer(txt))
    if hits:
        print(f"{c.get('name')}: {sorted(hits)}")
        print("   ", {k: c.get(k) for k in ("description", "category") if c.get(k)})

# top-level source / geographic scope blocks
print("\n== source block ==")
print(json.dumps(y["tables"][0]["source"], indent=2)[:2000])
print("\n== geographic scope ==")
print(json.dumps(y["tables"][0]["geographic_scope"], indent=2)[:1500])
print("\n== conventions ==")
for cv in y.get("conventions", []):
    print("-", cv.get("id"), "|", cv.get("rule", "")[:300].replace("\n", " "))
