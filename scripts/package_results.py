"""Archive one completed test run, its intermediate features and training provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='runs/full_baseline')
    parser.add_argument('--report', default='reports/full_baseline')
    parser.add_argument('--checkpoint', default='checkpoints/camus_full')
    parser.add_argument('--output', default='release_results')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    run, report, checkpoint, out = (Path(p).resolve() for p in
                                   (args.run, args.report, args.checkpoint, args.output))
    if not all(p.is_relative_to(root) for p in (run, report, checkpoint, out)):
        raise ValueError('All artifact paths must remain in the project directory')
    summary = json.loads((run / 'summary.json').read_text(encoding='utf-8'))
    if summary['cases_failed'] or summary['split'] != 'test' or summary['patients_attempted'] != 82:
        raise ValueError('Expected the completed predefined 82-patient test evaluation')
    if sha(checkpoint / 'best.pt') != summary['weights_sha256']:
        raise ValueError('Checkpoint does not match the evaluated model')
    files = sorted(p for folder in (run, report) for p in folder.rglob('*') if p.is_file())
    files += [checkpoint / 'run.json', checkpoint / 'training.csv',
              Path('reports/input_equivalence.json').resolve(),
              Path('reports/source_integrity.json').resolve(),
              Path('data/licenses/CAMUS_LICENSE_TERMS.md').resolve(),
              Path('vendor/echonet/LICENSE').resolve(),
              Path('vendor/echonet_source.json').resolve(),
              Path('data/manifests/echonet_weights.json').resolve()]
    if not all(p.is_file() for p in files):
        raise FileNotFoundError('A required provenance or license file is missing')
    out.mkdir(parents=True, exist_ok=True)
    archive = out / 'CAMUS_EchoNet_full_baseline_v0.4.0.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in files:
            bundle.write(path, path.relative_to(root).as_posix())
    manifest = {'scope': 'full_CAMUS_predefined_patient_test_split',
                'patients_attempted': summary['patients_attempted'],
                'cases_attempted': summary['cases_attempted'],
                'cases_failed': summary['cases_failed'],
                'evaluation_code_commit': summary['git_commit'],
                'artifacts': [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
                              for p in (archive, checkpoint / 'best.pt')]}
    (out / 'artifacts.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (out / 'SHA256SUMS.txt').write_text(''.join(f"{x['sha256']}  {x['file']}\n"
                                              for x in manifest['artifacts']), encoding='ascii')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
