"""Fetch original CAMUS 2CH/4CH cine sequences from the official Girder API."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _get_json(url: str):
    last_error = None
    for attempt in range(4):
        try:
            request = Request(url, headers={"User-Agent": "lvseg-research-baseline/1.0"})
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Unable to read official CAMUS inventory: {url}") from last_error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _requested_files(patient: dict) -> list[dict]:
    selected = []
    for entry in patient["files"]:
        name = Path(entry["path"]).name
        if name == "MANDATORY_CITATION.md" or name in {"Info_2CH.cfg", "Info_4CH.cfg"}:
            selected.append(entry)
        elif "_half_sequence.nii.gz" in name or "_half_sequence_gt.nii.gz" in name:
            selected.append(entry)
    expected = {f"{patient['patient_id']}_{view}_half_sequence{suffix}.nii.gz"
                for view in ("2CH", "4CH") for suffix in ("", "_gt")}
    actual = {Path(row["path"]).name for row in selected if "half_sequence" in row["path"]}
    if not expected <= actual:
        raise ValueError(f"Official inventory is missing a cine or label volume for {patient['patient_id']}")
    return selected


def _list_patient_items(base_url: str, patient: dict) -> dict:
    query = urlencode({"folderId": patient["girder_id"]})
    items = _get_json(f"{base_url}/item?{query}")
    return {item.get("name"): item for item in items}


def _download_one(base_url: str, item: dict, entry: dict, output_root: Path) -> dict:
    patient_dir = output_root / Path(entry["path"]).parent
    patient_dir.mkdir(parents=True, exist_ok=True)
    target = output_root / entry["path"]
    if target.is_file():
        if target.stat().st_size == entry["bytes"] and _sha256(target) == entry["sha256"]:
            return {"path": entry["path"], "bytes": entry["bytes"],
                    "sha256": entry["sha256"], "status": "verified_existing"}
        raise ValueError(f"Existing raw file fails its official checksum; preserved: {target}")

    if not item:
        raise FileNotFoundError(f"Official CAMUS folder does not contain {target.name}")
    if int(item.get("size", -1)) != entry["bytes"]:
        raise ValueError(f"Official CAMUS size changed for {entry['path']}")

    partial = target.with_name(target.name + ".partial")
    last_error = None
    for attempt in range(4):
        try:
            request = Request(f"{base_url}/item/{item['_id']}/download",
                              headers={"User-Agent": "lvseg-research-baseline/1.0"})
            with urlopen(request, timeout=180) as response, partial.open("wb") as stream:
                digest = hashlib.sha256()
                size = 0
                while block := response.read(1024 * 1024):
                    stream.write(block)
                    digest.update(block)
                    size += len(block)
            if size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"Official checksum mismatch for {entry['path']}")
            partial.replace(target)
            return {"path": entry["path"], "bytes": size,
                    "sha256": digest.hexdigest(), "status": "downloaded"}
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to retrieve {entry['path']}: {last_error}") from last_error


def download_camus(inventory_path: str | Path, output_root: str | Path,
                   *, workers: int = 4, patient_limit: int | None = None) -> dict:
    """Download original cine/image-label volumes and timing metadata.

    Download scope is 2CH/4CH half-sequences plus expert label volumes and
    per-view Info.cfg. The source's complete file inventory remains the
    authority for completeness; this does not claim full-folder retrieval.
    """
    inventory_path = Path(inventory_path)
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    if not inventory.get("complete") or len(inventory.get("patients", [])) != 500:
        raise ValueError("Expected the verified 500-patient CAMUS inventory")
    if workers < 1:
        raise ValueError("workers must be a positive integer")
    patients = inventory["patients"][:patient_limit] if patient_limit else inventory["patients"]
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    tasks = []
    with ThreadPoolExecutor(max_workers=min(workers, 8)) as pool:
        folders = {pool.submit(_list_patient_items, inventory["source"], patient): patient
                   for patient in patients}
        for future in as_completed(folders):
            patient = folders[future]
            items = future.result()
            for entry in _requested_files(patient):
                item = items.get(Path(entry["path"]).name)
                if item is None:
                    raise FileNotFoundError(f"Official CAMUS folder does not contain {entry['path']}")
                tasks.append((item, entry))
    results, failures = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_download_one, inventory["source"], item, entry, output_root): entry
                   for item, entry in tasks}
        for index, future in enumerate(as_completed(futures), start=1):
            entry = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                failures.append({"path": entry["path"], "error": str(error)})
            if index % 100 == 0 or index == len(futures):
                print(f"CAMUS files checked: {index}/{len(futures)}", flush=True)

    downloaded_bytes = sum(row["bytes"] for row in results)
    manifest = {
        "dataset": "CAMUS",
        "source_inventory": str(inventory_path),
        "source_inventory_sha256": _sha256(inventory_path),
        "source": inventory["source"],
        "license": "CC BY-NC-SA 4.0; non-commercial research; cite Leclerc et al., IEEE TMI 2019",
        "scope": "2CH/4CH half-sequence B-mode cine, corresponding reference masks, Info.cfg, citation",
        "patients_requested": len(patients),
        "patients_expected": 500,
        "files_expected": len(tasks),
        "files_verified": len(results),
        "bytes_verified": downloaded_bytes,
        "complete": not failures and len(results) == len(tasks) and len(patients) == 500,
        "files": sorted(results, key=lambda row: row["path"]),
        "failures": failures,
    }
    manifest_path = output_root / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if failures:
        raise RuntimeError(f"CAMUS download incomplete: {len(failures)} files failed; see {manifest_path}")
    return {key: manifest[key] for key in
            ("patients_requested", "files_expected", "files_verified", "bytes_verified", "complete")}
