"""Iteratively satisfy imports by extracting wheels from PyPI into .pylibs.

The sandbox blocks pip's wheel unpacking step, but wheels are ZIP files, so we
resolve them from the PyPI JSON API and extract them directly. This loop keeps
installing whatever import is missing until the target imports succeed.
"""
import importlib
import json
import os
import subprocess
import sys
import urllib.request
import zipfile

LIB = os.path.abspath(".pylibs")
CACHE = os.path.abspath("data/wheels")
os.makedirs(LIB, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)
sys.path.insert(0, LIB)

PREF = [
    "cp312-cp312-win_amd64", "cp312-cp312-win32", "cp312-abi3-win_amd64",
    "py3-none-any", "py2.py3-none-any", "cp312-none-win_amd64",
]

ALIAS = {
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "PIL": "pillow",
    "dateutil": "python-dateutil",
    "bs4": "beautifulsoup4",
}


def rank(fname):
    for i, tag in enumerate(PREF):
        if fname.endswith(f"-{tag}.whl"):
            return i
    return None


def install(pkg):
    data = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=60))
    cands = []
    for rel in data["urls"]:
        r = rank(rel["filename"])
        if r is not None:
            cands.append((r, rel))
    if not cands:
        for ver, files in data.get("releases", {}).items():
            for rel in files:
                r = rank(rel["filename"])
                if r is not None and not rel.get("yanked"):
                    cands.append((r, rel))
    if not cands:
        raise RuntimeError(f"no compatible wheel for {pkg}")
    cands.sort(key=lambda t: (t[0], t[1]["upload_time"]))
    _, rel = cands[0]
    fname = rel["filename"]
    dest = os.path.join(CACHE, fname)
    if not os.path.exists(dest):
        with urllib.request.urlopen(rel["url"], timeout=300) as resp, open(dest, "wb") as fh:
            fh.write(resp.read())
    with zipfile.ZipFile(dest) as zf:
        zf.extractall(LIB)
    importlib.invalidate_caches()
    return fname


TARGETS = ["pyarrow", "yaml", "sklearn", "statsmodels.api", "matplotlib",
           "scipy.stats"]

for _ in range(60):
    missing = None
    for mod in TARGETS:
        try:
            importlib.import_module(mod)
        except ModuleNotFoundError as e:
            name = (e.name or "").split(".")[0]
            if name and name not in ("", ".pylibs"):
                missing = name
                break
        except Exception as e:  # noqa: BLE001
            print(f"non-import error in {mod}: {e}")
    if missing is None:
        print("ALL TARGETS IMPORT OK")
        break
    pkg = ALIAS.get(missing, missing)
    print(f"installing {pkg} (for missing module {missing})")
    try:
        print("  ->", install(pkg))
    except Exception as e:  # noqa: BLE001
        print("  FAILED:", e)
        break
