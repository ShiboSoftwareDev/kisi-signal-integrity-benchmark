"""Prepare pinned, unmodified native tools in ignored local directories."""

import argparse
import hashlib
import io
import json
import subprocess
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((ROOT / "provenance/toolchain.lock.json").read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "kisi-signal-integrity-benchmark"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def link(destination, source):
    source = source.resolve(strict=True)
    if destination.is_symlink():
        if destination.resolve() != source:
            raise SystemExit(f"Existing link points elsewhere: {destination}")
    elif destination.exists():
        raise SystemExit(f"Refusing to replace existing path: {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source, target_is_directory=source.is_dir())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pipeline", type=Path, help="Reuse an exact upstream source directory"
    )
    parser.add_argument(
        "--kisi-source", type=Path, help="Reuse an unmodified pinned Kisi Git checkout"
    )
    parser.add_argument(
        "--kisi-cli", type=Path, help="Reuse the official release kisi.mjs"
    )
    parser.add_argument(
        "--models",
        type=Path,
        help="Directory containing the two original manufacturer IBIS files",
    )
    args = parser.parse_args()
    cache = ROOT / ".cache"
    pipeline = (args.pipeline or cache / "upstream/pipeline").resolve()
    if not pipeline.exists():
        if args.pipeline:
            raise SystemExit(f"Source directory does not exist: {pipeline}")
        archive = fetch(PINS["pipeline"]["archive_url"])
        if hashlib.sha256(archive).hexdigest() != PINS["pipeline"]["archive_sha256"]:
            raise SystemExit(
                "Pipeline archive checksum mismatch; source was not installed"
            )
        pipeline.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for member in tar.getmembers():
                parts = Path(member.name).parts[1:]
                if not parts:
                    continue
                member.name = str(Path(*parts))
                tar.extract(member, pipeline, filter="data")
    mismatches = [
        name
        for name, sha in PINS["pipeline"]["source_files_sha256"].items()
        if not (pipeline / name).is_file() or digest(pipeline / name) != sha
    ]
    if mismatches:
        raise SystemExit("Pipeline source checksum mismatch: " + ", ".join(mismatches))
    if args.pipeline:
        link(cache / "upstream/pipeline", pipeline)
    link(ROOT / "native/pipeline", pipeline)
    # Linking an as-yet uninstalled default node_modules is deliberate. The
    # documented frozen pnpm install populates it; no shared install is mutated.
    modules = ROOT / "native/node_modules"
    if not modules.exists() and not modules.is_symlink():
        modules.symlink_to(pipeline / "node_modules", target_is_directory=True)

    kisi = (args.kisi_source or cache / "upstream/kisi").resolve()
    if not kisi.exists():
        if args.kisi_source:
            raise SystemExit(f"Source directory does not exist: {kisi}")
        kisi.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--no-checkout", PINS["kisi"]["repository"], str(kisi)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(kisi), "checkout", "--detach", PINS["kisi"]["commit"]],
            check=True,
        )
    commit = subprocess.check_output(
        ["git", "-C", str(kisi), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != PINS["kisi"]["commit"]:
        raise SystemExit("Kisi checkout is not the pinned commit")
    validator = kisi / "validation/channel_export/compare.py"
    if digest(validator) != PINS["kisi"]["validator_sha256"]:
        raise SystemExit("Kisi validator has been modified")
    if args.kisi_source:
        link(cache / "upstream/kisi", kisi)
    cli = (args.kisi_cli or cache / "tools/kisi.mjs").resolve()
    if not cli.exists():
        if args.kisi_cli:
            raise SystemExit(f"CLI does not exist: {cli}")
        payload = fetch(PINS["kisi"]["cli_url"])
        if hashlib.sha256(payload).hexdigest() != PINS["kisi"]["cli_sha256"]:
            raise SystemExit("Kisi release checksum mismatch")
        cli.parent.mkdir(parents=True, exist_ok=True)
        cli.write_bytes(payload)
    if digest(cli) != PINS["kisi"]["cli_sha256"]:
        raise SystemExit("Kisi release checksum mismatch")
    if args.kisi_cli:
        link(cache / "tools/kisi.mjs", cli)

    models = (args.models or ROOT / ".local/models").resolve()
    lock = json.loads((ROOT / "provenance/vendor-models.lock.json").read_text())
    for name in ("cmos", "rs485"):
        model = lock["models"][name]
        path = models / model["file"]
        if not path.is_file() or digest(path) != model["sha256"]:
            raise SystemExit(
                f"Supply original {model['file']} matching the vendor lockfile in {models}; see docs/reproducing.md"
            )
    link(ROOT / "native/models", models)
    print(
        "Pinned source, CLI, and vendor model hashes verified; native links prepared."
    )
    print(
        "Install upstream dependencies with frozen pnpm 11.25.0 if needed; see docs/reproducing.md."
    )


if __name__ == "__main__":
    main()
