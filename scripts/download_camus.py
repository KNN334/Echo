"""Download the original 2CH/4CH CAMUS cine videos and expert masks."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lvseg.data.camus_download import download_camus


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", default="docs/data_sources/camus_download_manifest.json")
    parser.add_argument("--output", default="data/raw/camus_video")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit-patients", type=int, help="Small partial download for a smoke check")
    args = parser.parse_args(argv)
    result = download_camus(Path(args.inventory), Path(args.output),
                            workers=args.workers, patient_limit=args.limit_patients)
    print(result, flush=True)
    return result


def cli():
    main()


if __name__ == "__main__":
    main()
