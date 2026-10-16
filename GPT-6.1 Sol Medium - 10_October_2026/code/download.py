"""Retrieve the exact public record, preserve its files and verify Zenodo MD5s."""
import hashlib, json, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
RAW.mkdir(parents=True, exist_ok=True)
url = 'https://zenodo.org/api/records/23189372'
record = json.loads(urllib.request.urlopen(url, timeout=90).read())
(RAW / 'record.json').write_text(json.dumps(record, indent=2))
for f in record['files']:
    if not f['key'].endswith(('.parquet', '.yaml', '.txt', '.csv', '.html')):
        continue
    p = RAW / f['key']
    if not p.exists() or hashlib.md5(p.read_bytes()).hexdigest() != f['checksum'].split(':')[1]:
        p.write_bytes(urllib.request.urlopen(f['links']['self'], timeout=90).read())
    assert 'md5:' + hashlib.md5(p.read_bytes()).hexdigest() == f['checksum'], p
    print(p.name, p.stat().st_size, 'MD5 verified')
