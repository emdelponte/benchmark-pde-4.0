"""Step 2: unpack the YAML data dictionary structure and non-weather variables."""
import fhb_env  # noqa: F401
import json
import os

import yaml

import fhb_env as env

with open(os.path.join(env.DATA, "FHBVer2DataDict.yaml"), encoding="utf-8") as fh:
    y = yaml.safe_load(fh)

tables = y["tables"]
print("n tables:", len(tables))
for t in tables:
    print("table keys:", list(t.keys()))
    for k, v in t.items():
        if isinstance(v, list):
            print(f"  {k}: list[{len(v)}]")
        elif isinstance(v, dict):
            print(f"  {k}: dict[{len(v)}] keys={list(v.keys())[:10]}")
        else:
            print(f"  {k}: {str(v)[:120]}")

t = tables[0]
var_key = None
for cand in ("variables", "fields", "columns", "entries"):
    if cand in t:
        var_key = cand
        break
print("\nusing variable list key:", var_key)
vars_ = t[var_key]
print("n variables:", len(vars_))
print("\nfirst 3 full entries:")
for v in vars_[:3]:
    print(json.dumps(v, indent=2, ensure_ascii=False)[:3000])
    print("-" * 70)

names = [v.get("name") or v.get("variable_name") for v in vars_]
print("\nnon T./D./P./RH./VPD./TDD./TRH. names (likely design vars):")
for v in vars_:
    nm = v.get("name") or v.get("variable_name")
    if not any(str(nm).startswith(p) for p in ("T.", "D.", "P.", "RH.", "VPD.",
                                               "TDD.", "TRH.", "MT", "T1", "RH9",
                                               "RH8", "TRH9", "TRH8", "INT")):
        print(json.dumps(v, indent=2, ensure_ascii=False)[:2500])
        print("=" * 70)
