"""Create bounded GitHub Release archives; publish only after all 500 subjects verify."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',default='data/raw/CAMUS')
    p.add_argument('--output',default='release_data')
    a=p.parse_args()
    root,out=Path(a.root),Path(a.output)
    manifest=json.loads(Path('data/manifests/camus_download.json').read_text())
    if not manifest['complete'] or len(manifest['patients'])!=500:
        raise RuntimeError('refuse to publish an incomplete CAMUS dataset')
    out.mkdir(exist_ok=True)
    packs=[]
    for part,start in enumerate(range(0,500,100),1):
        archive=out/f'CAMUS_part_{part:02}_of_05.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as z:
            z.write('data/licenses/CAMUS_LICENSE_TERMS.md','CAMUS/LICENSE_TERMS.md')
            for record in manifest['patients'][start:start+100]:
                for f in record['files']:
                    path=root/f['path']
                    if not path.exists() or path.stat().st_size!=f['bytes']:
                        raise RuntimeError('missing file '+str(path))
                    digest=hashlib.sha256(path.read_bytes()).hexdigest()
                    if digest!=f['sha256']:raise RuntimeError('checksum mismatch '+str(path))
                    z.write(path,'CAMUS/'+f['path'])
        h=hashlib.sha256()
        with archive.open('rb') as src:
            for b in iter(lambda:src.read(1024*1024),b''):h.update(b)
        packs.append({'file':archive.name,'bytes':archive.stat().st_size,'sha256':h.hexdigest()})
    (out/'archives.json').write_text(json.dumps(packs,indent=2))
    (out/'SHA256SUMS.txt').write_text('\n'.join(x['sha256']+'  '+x['file'] for x in packs)+'\n')
    (out/'camus_download.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(packs,indent=2))


if __name__=='__main__':main()
