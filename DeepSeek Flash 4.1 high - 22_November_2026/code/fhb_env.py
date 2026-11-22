"""Shared environment bootstrap for the FHB analysis.

Import this FIRST in every analysis script:

    import fhb_env  # noqa: F401  (sets sys.path / matplotlib config)

Packages live in <workspace>/.pylibs because the sandbox blocked pip's wheel
unpacking; see code/_bootstrap_libs2.py and analysis_log.md.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, ".pylibs")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

# Matplotlib needs a writable cache dir inside the sandboxed workspace.
os.environ.setdefault("MPLCONFIGDIR", os.path.join(ROOT, ".mplconfig"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")

DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "outputs")
FIG = os.path.join(OUT, "figures")
for d in (DATA, OUT, FIG):
    os.makedirs(d, exist_ok=True)
