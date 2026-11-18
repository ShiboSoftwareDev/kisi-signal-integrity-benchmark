import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import skrf as rf

base = Path(
    os.environ.get(
        "BENCH_OUTPUT_DIR", Path(__file__).resolve().parents[1] / "build/native/results"
    )
)
for original in sorted(base.iterdir()):
    folder = original / "refinement4" if "--refinement4" in sys.argv else original
    meta = json.loads((folder / "metadata.json").read_text())
    maps = meta["mappings"]
    nodes = []
    for m in maps:
        nodes.extend([meta["node_map"][m["from"]], meta["node_map"][m["to"]]])
    count = len(nodes)
    s = np.zeros((1001, count, count), complex)
    portlist = [v for m in maps for v in [m["from"], m["to"]]]
    start = time.monotonic()
    for excitation in range(count):
        deck = [
            "Native routed passive channel AC",
            ".options klu reltol=1e-8 abstol=1e-13",
            (folder / "our-channel.lib").read_text(),
        ]
        for i, node in enumerate(nodes):
            deck.extend(
                [
                    f"VPORT{i} src{i} 0 DC 0 AC {2 if i==excitation else 0}",
                    f"RPORT{i} src{i} {node} 50",
                ]
            )
        deck.extend(
            [
                ".control",
                "set wr_vecnames",
                "ac lin 1001 1e6 1e10",
                "wrdata response.tsv " + " ".join(f"v({node})" for node in nodes),
                "quit",
                ".endc",
                ".end",
            ]
        )
        temp = folder / f"ac-{excitation}"
        temp.mkdir(exist_ok=True)
        (temp / "deck.cir").write_text("\n".join(deck) + "\n")
        r = subprocess.run(
            ["ngspice", "-n", "-b", "deck.cir"],
            cwd=temp,
            capture_output=True,
            text=True,
            timeout=180,
        )
        (temp / "solver.log").write_text(r.stdout + "\n" + r.stderr)
        if r.returncode:
            raise RuntimeError(r.stderr)
        a = np.loadtxt(temp / "response.tsv", skiprows=1)
        f = a[:, 0]
        for i in range(count):
            s[:, i, excitation] = (
                a[:, 3 * i + 1] + 1j * a[:, 3 * i + 2] - (i == excitation)
            )
        print(folder.name, "port", excitation, "done", flush=True)
    np.savez(folder / "our-channel.npz", frequency=f, s=s, source_port_ids=portlist)
    rf.Network(f=f, s=s, z0=50).write_touchstone(str(folder / "our-channel"))
    summary = {
        "ports": portlist,
        "nodes": nodes,
        "ac_seconds": time.monotonic() - start,
        "max_singular_value": float(np.linalg.svd(s, compute_uv=False)[:, 0].max()),
        "reciprocity_error": float(abs(s - s.transpose(0, 2, 1)).max()),
        "physical_termination_included": "differential" in meta["level"],
    }
    (folder / "our-ac-summary.json").write_text(json.dumps(summary, indent=2))
    print(folder.name, summary, flush=True)
