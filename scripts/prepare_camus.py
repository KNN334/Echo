"""Prepare verified CAMUS videos and fixed patient splits for LV segmentation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from lvseg.data.prepare_camus import prepare_camus


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/lvseg.yaml")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    data = config["dataset"]
    result = prepare_camus(data["raw_root"], data["prepared_root"],
                           data["fixed_patient_splits"],
                           image_hw=tuple(data["image_hw"]), overwrite=args.overwrite)
    Path(data["prepared_root"], "prepare_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    print(result, flush=True)
    return result


def cli():
    main()


if __name__ == "__main__":
    main()
