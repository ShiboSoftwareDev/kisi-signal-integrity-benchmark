"""Controlled diagnostic only: place our 120ohm load at Kisi's RX reference.
The original circuit and main comparison remain unchanged.
"""

import json
import os
import subprocess
from pathlib import Path

import numpy as np
import skrf as rf

base = (
    Path(
        os.environ.get(
            "BENCH_OUTPUT_DIR",
            Path(__file__).resolve().parents[1] / "build/native/results",
        )
    )
    / "level1-differential"
)
m = json.loads((base / "metadata.json").read_text())
nodes = [m["node_map"][p] for lane in m["mappings"] for p in [lane["from"], lane["to"]]]
lib = (base / "our-channel.lib").read_text()
old = next(x for x in lib.splitlines() if x.startswith("RPHYSICAL0 "))
new = f"RPHYSICAL0 {nodes[1]} {nodes[3]} 120"
assert old != new
lib = lib.replace(old, new)
out = base / "termination-location-control"
out.mkdir(exist_ok=True)
s = np.zeros((1001, 4, 4), complex)
for ex in range(4):
    deck = [
        "Diagnostic termination reference control",
        ".options klu reltol=1e-8 abstol=1e-13",
        lib,
    ]
    for i, node in enumerate(nodes):
        deck.extend(
            [f"VP{i} src{i} 0 AC {2 if i==ex else 0}", f"RP{i} src{i} {node} 50"]
        )
    deck += [
        ".control",
        "set wr_vecnames",
        "ac lin 1001 1e6 1e10",
        "wrdata ac.tsv " + " ".join(f"v({n})" for n in nodes),
        "quit",
        ".endc",
        ".end",
    ]
    (out / "deck.cir").write_text("\n".join(deck))
    r = subprocess.run(
        ["ngspice", "-n", "-b", "deck.cir"],
        cwd=out,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr
    a = np.loadtxt(out / "ac.tsv", skiprows=1)
    for i in range(4):
        s[:, i, ex] = a[:, 3 * i + 1] + 1j * a[:, 3 * i + 2] - (i == ex)
rf.Network(f=a[:, 0], s=s, z0=50).write_touchstone(str(out / "control"))
(out / "control.json").write_text(
    json.dumps(
        {
            "purpose": "Separate diagnostic of termination reference placement. Not an original-circuit result and not used in the main comparison.",
            "original_resistor": old,
            "diagnostic_resistor": new,
            "all_original_copper_stubs_preserved": True,
            "geometry_rerouted": False,
        },
        indent=2,
    )
)
print("Termination control complete")
