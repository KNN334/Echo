"""Resumable per-patient download from CAMUS' official public Girder service."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
import urllib.request
import zipfile

API = "https://humanheart-project.creatis.insa-lyon.fr/database/api/v1"
FOLDER = "63fde55f73e9f004868fb7ac"


def request(url, target=None):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                if target is None:
                    return json.load(r)
                with open(target, "wb") as f:
                    shutil.copyfileobj(r, f, 1024 * 1024)
                return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def fetch(folder, dest):
    patient = folder["name"]
    target = dest / patient
    marker = target / ".download_complete.json"
    if marker.exists():
        return json.loads(marker.read_text())
    archive = dest / (patient + ".download.zip")
    request(f"{API}/folder/{folder['_id']}/download", archive)
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            # Server ZIP prefixes vary. Keep the original basename inside this patient only.
            name = Path(info.filename).name
            if not name or name in {".", ".."}:
                raise ValueError("unsafe archive member")
            with z.open(info) as src, (target / name).open("wb") as out:
                shutil.copyfileobj(src, out)
    files = [{"path": str(p.relative_to(dest)).replace('\\', '/'), "bytes": p.stat().st_size,
              "sha256": digest(p)} for p in sorted(target.iterdir()) if p.is_file()]
    names={Path(x['path']).name for x in files}
    for view in ('2CH','4CH'):
        required=[f'Info_{view}.cfg']+[f'{patient}_{view}_{phase}{suffix}.nii.gz'
                  for phase in ('ED','ES') for suffix in ('','_gt')]
        if not all(name in names for name in required):
            raise RuntimeError('incomplete patient archive: missing phase image/config/label')
        if not any(f'{patient}_{view}_{s}.nii.gz' in names for s in ('sequence','half_sequence')):
            raise RuntimeError('missing sequence image')
    expected=folder.get('size')
    if expected is not None and sum(f['bytes'] for f in files)!=expected:
        raise RuntimeError('archive total bytes differ from official folder metadata')
    record = {"patient_id": patient, "girder_id": folder["_id"], "files": files}
    marker.write_text(json.dumps(record, indent=2), encoding="utf-8")
    archive.unlink()
    return record


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="data/raw/CAMUS")
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=8)
    a = p.parse_args()
    dest = Path(a.output)
    dest.mkdir(parents=True, exist_ok=True)
    folders = request(f"{API}/folder?parentType=folder&parentId={FOLDER}&limit=0&sort=name")
    folders = [f for f in folders if f["name"].startswith("patient")]
    selected = folders[:a.limit] if a.limit else folders
    manifest = {"source": API, "folder_id": FOLDER, "expected_patients": len(folders),
                "retrieved_utc": datetime.now(timezone.utc).isoformat(), "patients": [], "failures": []}
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        tasks = {pool.submit(fetch, f, dest): f["name"] for f in selected}
        for future in as_completed(tasks):
            try:
                manifest["patients"].append(future.result())
            except Exception as e:
                manifest["failures"].append({"patient_id": tasks[future], "error": str(e)})
                print(f"FAILED {tasks[future]}: {type(e).__name__}: {e}",flush=True)
            count = len(manifest["patients"]) + len(manifest["failures"])
            if count % 10 == 0 or count == len(selected):
                print(f"CAMUS {count}/{len(selected)}, failed {len(manifest['failures'])}", flush=True)
                Path('data/manifests').mkdir(parents=True,exist_ok=True)
                Path('data/manifests/camus_download_progress.json').write_text(json.dumps(manifest,indent=2))
    manifest["patients"].sort(key=lambda x: x["patient_id"])
    manifest["complete"] = len(manifest["patients"]) == len(folders) and not manifest["failures"]
    out = Path("data/manifests/camus_download.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if manifest["failures"]:
        raise SystemExit("Download incomplete; rerun to retry failed patients")


if __name__ == "__main__":
    main()
