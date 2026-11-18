"""Verify frozen evidence, or recompute the common comparison."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify():
    manifest = json.loads((ROOT / "provenance/manifest.json").read_text())
    failures = []
    for name, expected in manifest["sha256"].items():
        path = ROOT / name
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            failures.append(name)
    if failures:
        raise SystemExit("Evidence checksum mismatch: " + ", ".join(failures))
    print(f"Verified {len(manifest['sha256'])} frozen evidence files.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="Verify checksums of the published evidence")
    analysis = sub.add_parser(
        "reanalyze", help="Recompute metrics and plot from native channels"
    )
    analysis.add_argument("--data", type=Path, default=ROOT / "data/cases")
    analysis.add_argument("--output", type=Path, default=ROOT / "build/reanalysis")
    analysis.add_argument("--refinement", type=int, choices=[2, 4], default=4)
    args = parser.parse_args()
    if args.command == "verify":
        verify()
    else:
        from .analysis import analyze
        from .plot import plot

        summary = analyze(args.data, args.output, args.refinement)
        plot(summary, args.output)
        print(f"Reanalysis written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
