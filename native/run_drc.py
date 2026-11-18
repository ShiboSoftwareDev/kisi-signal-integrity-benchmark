"""Run KiCad DRC without hiding violations or changing any copper."""

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.environ.get("BENCH_OUTPUT_DIR", ROOT / "build/native/results"))
for folder in sorted(BASE.iterdir()):
    command = [
        os.environ.get("KICAD_CLI", "kicad-cli"),
        "pcb",
        "drc",
        "--format",
        "json",
        "--output",
        str(folder / "kicad-drc.json"),
        str(folder / "board.kicad_pcb"),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=180)
    (folder / "kicad-drc.log").write_text(result.stdout + "\n" + result.stderr)
    result.check_returncode()
    report = json.loads((folder / "kicad-drc.json").read_text())
    shorts = sum(v["type"] == "shorting_items" for v in report["violations"])
    print(f"{folder.name}: {shorts} shorting_items violations")
