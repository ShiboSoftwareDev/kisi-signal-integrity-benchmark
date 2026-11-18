import json
import os
import subprocess
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = Path(os.environ.get("BENCH_OUTPUT_DIR", root / "build/native/results"))
env = {**os.environ, "KISI_THREADS": "1", "KISI_CACHE": str(root / ".cache/kisi")}
for folder in sorted(base.iterdir()):
    board = folder / "board.kicad_pcb"
    for label, args in [
        ("config-check", ["config-check", str(board)]),
        ("interfaces", ["interfaces", str(board)]),
        ("check", ["check", str(board), "--all", "--roughness", "smooth"]),
        (
            "crosstalk",
            [
                "crosstalk",
                str(board),
                "--all",
                "--rise-ps",
                "100",
                "--roughness",
                "smooth",
            ],
        ),
    ]:
        start = time.monotonic()
        r = subprocess.run(
            ["node", str(root / ".cache/tools/kisi.mjs"), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        (folder / f"kisi-{label}.json").write_text(r.stdout)
        (folder / f"kisi-{label}.log").write_text(r.stderr)
        r.check_returncode()
        print(
            folder.name,
            label,
            r.returncode,
            round(time.monotonic() - start, 2),
            flush=True,
        )
    audit = json.loads((folder / "export-audit.json").read_text())
    for net in audit["signal_net_names"][
        : 1 if "differential" in folder.name else None
    ]:
        args = [
            "export",
            str(board),
            "--lane",
            net,
            "--roughness",
            "smooth",
            "--fmax",
            "10",
            "--fmin",
            ".01",
            "--format",
            "lib,spice,touchstone",
            "--out",
            str(folder / "kisi" / net),
        ]
        r = subprocess.run(
            ["node", str(root / ".cache/tools/kisi.mjs"), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        (folder / f"kisi-export-{net}.json").write_text(r.stdout)
        (folder / f"kisi-export-{net}.log").write_text(r.stderr)
        r.check_returncode()
        print(folder.name, "export", net, r.returncode, flush=True)

# Extra low-frequency sample anchors DC gain without output normalization.
for folder in sorted(base.iterdir()):
    audit = json.loads((folder / "export-audit.json").read_text())
    for net in audit["signal_net_names"][
        : 1 if "differential" in folder.name else None
    ]:
        args = [
            "export",
            str(folder / "board.kicad_pcb"),
            "--lane",
            net,
            "--roughness",
            "smooth",
            "--fmax",
            ".001",
            "--fmin",
            ".000001",
            "--format",
            "touchstone",
            "--out",
            str(folder / "kisi-dc" / net),
        ]
        r = subprocess.run(
            ["node", str(root / ".cache/tools/kisi.mjs"), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        (folder / f"kisi-dc-{net}.json").write_text(r.stdout)
        r.check_returncode()
        print(folder.name, "DC anchor", net, r.returncode, flush=True)
