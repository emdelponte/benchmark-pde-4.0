import urllib.request, os, hashlib
base = "https://zenodo.org/api/records/23189372/files"
files = ["FHBVer2.parquet","FHBVer2DataDict.yaml","README.txt","VariablesMetaData.csv","FHBVer2Codebook.pdf"]
os.makedirs("data", exist_ok=True)
for f in files:
    url = f"{base}/{f}/content"
    p = os.path.join("data", f)
    with urllib.request.urlopen(url, timeout=120) as r, open(p, "wb") as fh:
        fh.write(r.read())
    print(f, os.path.getsize(p))
