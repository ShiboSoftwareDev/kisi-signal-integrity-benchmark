import json
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for level, lane in [
    ("level1-single-ended", "DATA"),
    ("level1-differential", "BUS_P"),
    ("level2-two-channels", "D0"),
]:
    folder = (
        Path(os.environ.get("BENCH_OUTPUT_DIR", root / "build/native/results")) / level
    )
    args = [
        str(Path(sys.executable)),
        str(root / ".cache/upstream/kisi/validation/channel_export/compare.py"),
        str(root / "native/kisi-cli"),
        str(folder / "board.kicad_pcb"),
        "--out",
        str(folder / "native-export-validation"),
        "--lane",
        lane,
        "--models",
        "ladder,compact",
        "--fmax",
        "10",
        "--passivity",
        "--transient",
        "--strict",
        "--report",
        str(folder / "native-export-validation.md"),
    ]
    r = subprocess.run(
        args,
        env={**os.environ, "MPLCONFIGDIR": str(root / ".cache/matplotlib")},
        capture_output=True,
        text=True,
        timeout=240,
    )
    (folder / "native-export-validation.log").write_text(r.stdout + "\n" + r.stderr)
    (folder / "native-export-validation-status.json").write_text(
        json.dumps(
            {
                "exit_code": r.returncode,
                "command": args,
                "kisi_roughness": "smooth",
                "strict": True,
            },
            indent=2,
        )
    )
    print(level, "exit", r.returncode, r.stdout[-2200:], flush=True)

    expected = 1 if level == "level1-differential" else 0
    if r.returncode != expected:
        raise RuntimeError(
            f"{level}: unexpected validator status {r.returncode}, expected {expected}; inspect native log"
        )

    report = json.loads((folder / "native-export-validation/results.json").read_text())
    if len(report["lanes"]) != 2 or any(
        "step" not in result for result in report["lanes"]
    ):
        raise RuntimeError(f"{level}: incomplete native validation report")
    if expected == 1 and not all(
        result["step"]["max_diff_of_final"] > 0.05 for result in report["lanes"]
    ):
        raise RuntimeError(
            "BUS_P failed for a different reason than the recorded step-fidelity issue"
        )
