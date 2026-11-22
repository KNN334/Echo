"""Prepare EchoNet-Dynamic videos for the shared downstream baseline."""

from pathlib import Path
import argparse
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lvseg.data.prepare_echonet import prepare_echonet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", required=True,
                        help="EchoNet-Dynamic root containing FileList.csv, Videos and VolumeTracings.csv")
    parser.add_argument("--output", default="data/processed/echonet")
    parser.add_argument("--height", type=int, default=192)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--limit", type=int, default=None)
    options = parser.parse_args(argv)
    result = prepare_echonet(options.raw_root, options.output,
                             image_hw=(options.height, options.width), limit=options.limit)
    print(result, flush=True)
    return result


def cli():
    main()


if __name__ == "__main__":
    cli()
