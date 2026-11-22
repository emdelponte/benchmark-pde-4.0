"""Step 1: inspect record contents -- YAML structure, parquet schema, metadata CSV."""
import fhb_env  # noqa: F401
import json
import os
import sys

import pandas as pd
import pyarrow.parquet as pq
import yaml

import fhb_env as env

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)

print("=" * 90)
print("PARQUET FILE SCHEMA")
print("=" * 90)
pf = pq.ParquetFile(os.path.join(env.DATA, "FHBVer2.parquet"))
print("rows:", pf.metadata.num_rows, "cols:", pf.metadata.num_columns,
      "row_groups:", pf.metadata.num_row_groups)
sch = pf.schema_arrow
for f in sch:
    print(f"{f.name:<28} {str(f.type):<12} {f.metadata}")
df = pq.read_table(os.path.join(env.DATA, "FHBVer2.parquet")).to_pandas()
print("\npandas shape:", df.shape)
print("\ndtypes counts:")
print(df.dtypes.astype(str).value_counts())
df.to_pickle(os.path.join(env.OUT, "fhb_raw.pkl"))

print("\n" + "=" * 90)
print("YAML TOP-LEVEL KEYS")
print("=" * 90)
with open(os.path.join(env.DATA, "FHBVer2DataDict.yaml"), encoding="utf-8") as fh:
    y = yaml.safe_load(fh)
print(type(y), list(y.keys()) if isinstance(y, dict) else len(y))
for k, v in y.items():
    if isinstance(v, dict):
        print(f"  {k}: dict[{len(v)}] keys={list(v.keys())[:8]}")
    elif isinstance(v, list):
        print(f"  {k}: list[{len(v)}]")
    else:
        print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")

print("\n" + "=" * 90)
print("VARIABLES METADATA CSV")
print("=" * 90)
vm = pd.read_csv(os.path.join(env.DATA, "VariablesMetaData.csv"))
print(vm.shape)
print(vm.columns.tolist())
print(vm.head(10).to_string())
print("\nperiod value counts:")
print(vm["period"].value_counts(dropna=False))
print("\ntype value counts:")
print(vm["type"].value_counts(dropna=False))
