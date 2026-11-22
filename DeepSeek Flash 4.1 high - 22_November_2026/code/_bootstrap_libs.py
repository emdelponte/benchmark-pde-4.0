"""Bootstrap pure-wheel installs into ./.pylibs without pip.

Rationale: pip could not unpack wheels inside the sandboxed workspace
(OSError EACCES on *.whl.metadata). Wheels are ZIP archives, so we resolve
them from the PyPI JSON API and extract them directly. Recorded in
analysis_log.md as a computational workaround.
"""
import json
import os
import sys
import urllib.request
import zipfile

LIB = os.path.abspath(".pylibs")
CACHE = os.path.abspath("data/wheels")
os.makedirs(LIB, exist_ok=True)
os.makedirs(CACHE, exist_ok=True)

PREF = [
    "cp312-cp312-win_amd64",
    "cp312-cp312-win32",
    "cp312-abi3-win_amd64",
    "py3-none-any",
    "py2.py3-none-any",
    "cp312-none-win_amd64",
]

PACKAGES = sys.argv[1:]
if not PACKAGES:
    PACKAGES = ["pyyaml", "pyarrow", "scipy", "joblib", "threadpoolctl",
                "scikit-learn", "patsy", "statsmodels", "contourpy", "cycler",
                "fonttools", "kiwisolver", "packaging", "pyparsing",
                "matplotlib"]


def rank(fname):
    for i, tag in enumerate(PREF):
        if fname.endswith(f"-{tag}.whl"):
            return i
    return None


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


for pkg in PACKAGES:
    try:
        data = get_json(f"https://pypi.org/pypi/{pkg}/json")
    except Exception as e:  # noqa: BLE001
        print(f"SKIP {pkg}: metadata error {e}")
        continue
    cands = []
    for rel in data["urls"]:
        r = rank(rel["filename"])
        if r is not None:
            cands.append((r, rel))
    if not cands:
        # fall back: scan all releases for a compatible wheel
        for ver, files in data["releases"].items():
            for rel in files:
                r = rank(rel["filename"])
                if r is not None and rel.get("yanked") is not True:
                    cands.append((r, rel))
    if not cands:
        print(f"SKIP {pkg}: no compatible wheel found")
        continue
    cands.sort(key=lambda t: (t[0], t[1]["upload_time"]))
    r, rel = cands[0]
    fname = rel["filename"]
    dest = os.path.join(CACHE, fname)
    if not os.path.exists(dest):
        print(f"GET  {pkg}: {fname} ({rel['size']/1e6:.1f} MB)")
        with urllib.request.urlopen(rel["url"], timeout=300) as resp, open(dest, "wb") as fh:
            fh.write(resp.read())
    else:
        print(f"HAVE {pkg}: {fname}")
    with zipfile.ZipFile(dest) as zf:
        zf.extractall(LIB)
    print(f"OK   {pkg} -> extracted {fname}")

print("done")
