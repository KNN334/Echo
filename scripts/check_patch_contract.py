"""Validate a patch acquisition record and print its permitted outputs."""

from pathlib import Path
import argparse
import json
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.patch.contract import load_patch_record, validate_patch_record


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a patch acquisition record")
    parser.add_argument("record", help="JSON or YAML patch record")
    parser.add_argument("--require-data", action="store_true")
    args = parser.parse_args(argv)
    report = validate_patch_record(load_patch_record(args.record), require_data=args.require_data)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
