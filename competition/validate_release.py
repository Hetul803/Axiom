import json, hashlib, tarfile, io, base64, re
from pathlib import Path
REL=Path(__file__).resolve().parent/'release'
def main():
    manifest=json.loads((REL/'manifest.json').read_text()); bundle=(REL/'agent_bundle.py').read_text(); m=re.search(r"DATA='([^']+)'", bundle); assert m, 'missing DATA bundle'
    raw=base64.b64decode(m.group(1)); assert hashlib.sha256(raw).hexdigest()==manifest['bundle_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as tar:
        names=sorted(tar.getnames())
    assert sorted(manifest['files'])==names
    print('release validation passed')
if __name__=='__main__': main()
