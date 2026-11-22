"""Step 4: extract codebook PDF text and search for outcome/threshold definitions."""
import fhb_env  # noqa: F401
import os
import re

from pypdf import PdfReader

import fhb_env as env

pdf = os.path.join(env.DATA, "FHBVer2Codebook.pdf")
reader = PdfReader(pdf)
print("pages:", len(reader.pages))
texts = []
for i, p in enumerate(reader.pages):
    try:
        texts.append(p.extract_text() or "")
    except Exception as e:  # noqa: BLE001
        texts.append("")
        print("page", i, "error", e)
full = "\n\n<<<PAGE>>>\n\n".join(texts)
with open(os.path.join(env.OUT, "codebook_text.txt"), "w", encoding="utf-8") as fh:
    fh.write(full)
print("chars:", len(full))

pat = re.compile(r"epidemi\w*|binary|threshold|outbreak|dichotom|cut-?off|classif",
                 re.IGNORECASE)
for i, t in enumerate(texts):
    for m in pat.finditer(t):
        s = max(0, m.start() - 260)
        e = min(len(t), m.end() + 260)
        print(f"\n--- page {i+1} hit '{m.group(0)}' ---")
        print(t[s:e].replace("\n", " "))
