"""Preserve rendered copper and connectivity; translate only coordinates and names."""

import json
import math
import os
import uuid
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = Path(os.environ.get("BENCH_OUTPUT_DIR", root / "build/native/results"))
for folder in base.iterdir():
    c = json.loads((folder / "circuit.json").read_text())

    def by(t):
        return [r for r in c if r["type"] == t]

    m = json.loads((folder / "metadata.json").read_text())
    parent = {}

    def find(s):
        parent.setdefault(s, s)
        if parent[s] != s:
            parent[s] = find(parent[s])
        return parent[s]

    def union(a, b):
        parent[find(b)] = find(a)

    for trace in by("source_trace"):
        ports = trace["connected_source_port_ids"] + trace.get(
            "connected_source_net_ids", []
        )
        for p in ports[1:]:
            union(ports[0], p)
    groups = {}
    for n in by("source_net"):
        groups[find(n["source_net_id"])] = n["name"]
    diff = "differential" in folder.name
    for i, lane in enumerate(m["mappings"]):
        groups[find(lane["from"])] = (
            ("BUS_P" if i == 0 else "BUS_N") if diff else lane["port"]
        )
    all_ids = [r["source_port_id"] for r in by("source_port")] + [
        r["source_net_id"] for r in by("source_net")
    ]
    for i, p in enumerate(all_ids):
        groups.setdefault(find(p), f"UNCONNECTED_{i}")
    names = [""] + sorted(set(groups.values()))
    netid = {n: i for i, n in enumerate(names)}

    def net(p):
        return netid[groups[find(p)]]

    scomp = {r["source_component_id"]: r for r in by("source_component")}
    sp = {r["source_port_id"]: r for r in by("source_port")}
    pp = {r["pcb_port_id"]: r for r in by("pcb_port")}
    mapping = {}
    ic = 0
    rr = 0
    for r in by("source_component"):
        if r["ftype"] == "simple_chip":
            ic += 1
            mapping[r["name"]] = f"U{ic}"
        elif r["ftype"] == "simple_resistor":
            rr += 1
            mapping[r["name"]] = f"R{rr}"
    board = by("pcb_board")[0]
    w = board["width"]
    h = board["height"]
    cx = board["center"]["x"]
    cy = board["center"]["y"]

    def xy(x, y):
        return (x - cx + w / 2, h / 2 - (y - cy))

    def uid(s):
        return str(
            uuid.uuid5(uuid.NAMESPACE_URL, "kisi-three/" + folder.name + "/" + s)
        )

    stack = by("pcb_stackup")[0]["layers"]
    copper = [r for r in stack if r["layer_type"] == "copper"]
    layers = {"top": "F.Cu", "bottom": "B.Cu"}
    thickness = sum(r["thickness"] for r in stack)
    lines = [
        '(kicad_pcb (version 20241229) (generator "preserved_tscircuit_fixture")',
        f'(general (thickness {thickness})) (paper "A4")',
        '(layers (0 "F.Cu" signal) (2 "B.Cu" signal) (1 "F.Mask" user) (3 "B.Mask" user) (5 "F.SilkS" user) (25 "Edge.Cuts" user))',
        '(setup (stackup (layer "F.Mask" (type "Top Solder Mask") (thickness 0.02) (epsilon_r 3.3) (loss_tangent 0.025))',
    ]
    for i, r in enumerate(stack):
        if r["layer_type"] == "copper":
            lines.append(
                f'(layer "{layers[r["layer"]]}" (type "copper") (thickness {r["thickness"]}))'
            )
        else:
            lines.append(
                f'(layer "dielectric {i}" (type "core") (thickness {r["thickness"]}) (material "{r.get("material_name","FR4")}") (epsilon_r {r["relative_permittivity"]}) (loss_tangent 0.02))'
            )
    lines.append(
        '(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.02) (epsilon_r 3.3) (loss_tangent 0.025))))'
    )
    lines.extend(f'(net {i} "{n}")' for i, n in enumerate(names))
    for pc in by("pcb_component"):
        sc = scomp.get(pc.get("source_component_id"))
        pads = [
            p
            for p in by("pcb_smtpad")
            if p["pcb_component_id"] == pc["pcb_component_id"]
        ]
        if not sc or not pads:
            continue
        x, y = xy(pc["center"]["x"], pc["center"]["y"])
        ref = mapping[sc["name"]]
        value = str(
            sc.get("resistance", sc.get("manufacturer_part_number", sc["name"]))
        )
        lines.append(
            f'(footprint "Original:{sc["name"]}" (layer "F.Cu") (at {x} {y}) (uuid "{uid(pc["pcb_component_id"])}") (attr smd) (property "Reference" "{ref}" (at 0 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) (property "Value" "{value}" (at 0 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))))'
        )
        lines[-1] = lines[-1][:-1]
        for p in pads:
            px, py = xy(p["x"], p["y"])
            source = pp[p["pcb_port_id"]]["source_port_id"]
            pn = sp[source].get("pin_number", sp[source]["name"])
            ni = net(source)
            assert p["shape"] == "rect", p
            lines.append(
                f'(pad "{pn}" smd rect (at {px-x} {py-y}) (size {p["width"]} {p["height"]}) (layers "F.Cu" "F.Mask") (net {ni} "{names[ni]}") (uuid "{uid(p["pcb_smtpad_id"])}"))'
            )
        lines.append(")")
    keynets = {
        r["subcircuit_connectivity_map_key"]: (
            net(r["source_trace_id"])
            if r["source_trace_id"] in parent
            else net(
                (
                    r["connected_source_port_ids"]
                    + r.get("connected_source_net_ids", [])
                )[0]
            )
        )
        for r in by("source_trace")
    }
    tracenets = {
        r["source_trace_id"]: net(
            (r["connected_source_port_ids"] + r.get("connected_source_net_ids", []))[0]
        )
        for r in by("source_trace")
    }
    lengths = {}
    segments = []
    for t in by("pcb_trace"):
        n = tracenets.get(
            t.get("source_trace_id"),
            keynets.get(t.get("subcircuit_connectivity_map_key")),
        )
        assert n is not None, t
        for i, (a, b) in enumerate(zip(t["route"], t["route"][1:])):
            if b["route_type"] != "wire":
                continue
            layer = a["to_layer"] if a["route_type"] == "via" else a["layer"]
            if a["x"] == b["x"] and a["y"] == b["y"]:
                continue
            assert layer == b["layer"]
            ax, ay = xy(a["x"], a["y"])
            bx, byy = xy(b["x"], b["y"])
            width = b.get("width", a.get("width", 0.1))
            lines.append(
                f'(segment (start {ax} {ay}) (end {bx} {byy}) (width {width}) (layer "{layers[layer]}") (net {n}) (uuid "{uid(t["pcb_trace_id"]+str(i))}"))'
            )
            length = math.hypot(bx - ax, byy - ay)
            lengths[names[n]] = lengths.get(names[n], 0) + length
            segments.append((ax, ay, bx, byy, width, n))
    for v in by("pcb_via"):
        n = (
            net(v["source_net_id"])
            if v.get("source_net_id")
            else keynets.get(v.get("subcircuit_connectivity_map_key"))
        )
        assert n is not None, v
        x, y = xy(v["x"], v["y"])
        lines.append(
            f'(via (at {x} {y}) (size {v["outer_diameter"]}) (drill {v["hole_diameter"]}) (layers "F.Cu" "B.Cu") (net {n}) (uuid "{uid(v["pcb_via_id"])}"))'
        )
    for p in by("pcb_copper_pour"):
        n = net(p["source_net_id"])
        rings = [p["brep_shape"]["outer_ring"]] + p["brep_shape"]["inner_rings"]
        assert len(rings) == 1
        points = " ".join(
            f'(xy {xy(q["x"],q["y"])[0]} {xy(q["x"],q["y"])[1]})'
            for q in rings[0]["vertices"]
        )
        layer = layers[p["layer"]]
        lines.append(
            f'(zone (net {n}) (net_name "{names[n]}") (layer "{layer}") (uuid "{uid(p["pcb_copper_pour_id"])}") (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.001) (filled_areas_thickness no) (fill yes (thermal_gap 0.1) (thermal_bridge_width 0.1)) (polygon (pts {points})) (filled_polygon (layer "{layer}") (pts {points})))'
        )
    lines.append(
        f'(gr_rect (start 0 0) (end {w} {h}) (stroke (width 0.05) (type default)) (fill none) (layer "Edge.Cuts") (uuid "{uid("outline")}")))'
    )
    path = folder / "board.kicad_pcb"
    path.write_text("\n".join(lines) + "\n")
    (folder / "board.kicad_pro").write_text(
        json.dumps(
            {
                "meta": {"filename": "board.kicad_pro", "version": 1},
                "net_settings": {
                    "classes": [
                        {
                            "name": "Default",
                            "clearance": 0.1,
                            "track_width": 0.1,
                            "via_diameter": 0.3,
                            "via_drill": 0.2,
                        }
                    ]
                },
            }
        )
    )
    signalnames = [groups[find(lane["from"])] for lane in m["mappings"]]
    config = {
        "kisi_config": 1,
        "net_classes": {
            "Benchmark": {
                "nets": signalnames,
                "target_ohm": 100 if diff else 50,
                "diff": diff,
                "profile": "lvds" if diff else "se50",
                "source": {
                    "kind": "design",
                    "note": "Linear channel benchmark; does not assert original interface rate or controlled impedance.",
                },
            }
        },
    }
    (folder / "board.kisi.json").write_text(json.dumps(config, indent=2))
    manifest = {
        "level": folder.name,
        "reference_mapping": mapping,
        "net_names": names,
        "signal_net_names": signalnames,
        "source_port_to_net": {p: groups[find(p)] for p in all_ids},
        "lengths_mm": lengths,
        "segments": len(segments),
        "pads": len(by("pcb_smtpad")),
        "vias": len(by("pcb_via")),
        "pours": len(by("pcb_copper_pour")),
        "original_nominal_board_mm": board["thickness"],
        "actual_stack_mm": thickness,
        "coordinate_transform": "x_kicad=x-cx+width/2; y_kicad=height/2-(y-cy)",
        "routes_modified": False,
        "materials": "Exact generated stackup, plus the same declared mask and loss assumptions used by our extractor.",
        "known_render_errors": json.loads(
            (folder / "render-diagnostics.json").read_text()
        ),
    }
    (folder / "export-audit.json").write_text(json.dumps(manifest, indent=2))
    print(folder.name, signalnames, lengths)
