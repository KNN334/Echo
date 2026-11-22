"""Plot every inferred video frame and show predicted EDV/ESV extrema."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lvseg.visualization.volume_curve import plot_volume_curve


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, help="One model's evaluation directory")
    parser.add_argument("--case", required=True, help="For example patient0001_4CH")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    path = plot_volume_curve(args.results, args.case, args.output)
    print(path, flush=True)
    return path


def cli():
    main()


if __name__ == "__main__":
    main()
