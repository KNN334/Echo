import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def main():
    root=Path('data/processed/camus')
    manifest=json.loads((root/'manifest.json').read_text())
    if len(manifest['cases'])!=1000 or manifest['failures']:
        raise RuntimeError('full 1000-view preprocessing required')
    patients={x['patient_id'] for x in manifest['cases']}
    if len(patients)!=500 or sum(x['labeled_frames'] for x in manifest['cases'])!=2000:
        raise RuntimeError('patient or expert annotation count mismatch')
    provenance={'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'source_manifest_sha256':sha(Path('data/manifests/camus_download.json')),
                'config_sha256':sha(Path('configs/camus.json')),
                'split_sha256':sha(Path('data/manifests/splits.json')),
                'patients':500,'views':1000,'expert_labeled_frames':2000,
                'roi_manually_reviewed':False,'license':'CC BY-NC-SA 4.0'}
    target=Path('data/manifests/prepared_provenance.json')
    target.write_text(json.dumps(provenance,indent=2))
    out=Path('release_prepared');out.mkdir(exist_ok=True)
    archive=out/'prepared_camus.zip'
    paths=sorted(root.glob('*'))+[target,Path('data/manifests/splits.json'),Path('data/manifests/camus_download.json'),Path('data/licenses/CAMUS_LICENSE_TERMS.md')]
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
        for p in paths:
            if p.is_file():z.write(p,p.as_posix())
    digest=sha(archive)
    (out/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n')
    (out/'prepared_provenance.json').write_text(json.dumps({**provenance,'archive_sha256':digest,'bytes':archive.stat().st_size},indent=2))
    print(json.dumps(provenance,indent=2))


if __name__=='__main__':main()
