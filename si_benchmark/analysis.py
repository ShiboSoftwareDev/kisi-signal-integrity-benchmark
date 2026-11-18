"""Compare native extractions with explicit, identical linear excitations and loads."""

import json
from pathlib import Path

import numpy as np
import skrf as rf
from scipy.fft import irfft, rfft, rfftfreq
from scipy.interpolate import interp1d

ROOT = Path(__file__).resolve().parents[1]
CASES = ("level1-single-ended", "level1-differential", "level2-two-channels")
freq = np.arange(1001) * 1e7
ui = 1e-9
spui = 256
sigma = 100e-12 / 2.5631031310892007
edge = np.exp(-0.5 * (2 * np.pi * freq * sigma) ** 2) * np.exp(
    -2j * np.pi * freq * 5 * sigma
)
state = 127
bits = []
for _ in range(127):
    bit = ((state >> 6) ^ (state >> 5)) & 1
    state = ((state << 1) | bit) & 127
    bits.append(bit)
bits = np.array(bits)
x = np.repeat(bits, spui)
fft_freq = rfftfreq(len(x), ui / spui)


def channel(path, dcpath=None, reorder=None):
    n = rf.Network(str(path))
    f = n.f
    s = n.s
    if dcpath:
        dc = rf.Network(str(dcpath))
        f = np.r_[dc.f[0], f]
        s = np.concatenate([dc.s[:1], s])
    if reorder:
        s = s[:, reorder, :][:, :, reorder]
    return f, s


def response(f, s, diff, termination):
    p = s.shape[1]
    ident = np.eye(p)[None, :, :]
    y = np.linalg.solve(ident + s, ident - s) / 50
    load = np.zeros(p)
    load[: 2 if diff else p] = 1 / 50
    if diff:
        load[2:] = 1e-9
        if termination:
            y[:, 2, 2] += 1 / 120
            y[:, 3, 3] += 1 / 120
            y[:, 2, 3] -= 1 / 120
            y[:, 3, 2] -= 1 / 120
    mat = y + ident * (load[None, :] + 2j * np.pi * f[:, None] * 1e-12)[:, None, :]
    ins = [0] if diff or p == 2 else [0, 2]
    h = []
    for port in ins:
        drive = np.zeros((len(f), p), complex)
        if diff:
            drive[:, 0] = 1 / 50
            drive[:, 1] = -1 / 50
        else:
            drive[:, port] = 2 / 50
        v = np.linalg.solve(mat, drive[:, :, None])[:, :, 0]
        outputs = (
            (v[:, 2] - v[:, 3])[:, None] if diff else v[:, [1] if p == 2 else [1, 3]]
        )
        # Real DC anchor uses the native nearly-DC response, without voltage normalization.
        raw = interp1d(
            np.r_[0, f],
            np.concatenate([outputs[:1].real, outputs]),
            axis=0,
            bounds_error=False,
            fill_value=(outputs[0].real, outputs[-1]),
        )(freq)
        h.append(raw)
    return np.stack(h, axis=-1)  # frequency, output, input


def periodic(h):
    out = []
    for rx in range(h.shape[1]):
        y = np.zeros(len(x))
        for tx in range(h.shape[2]):
            hh = interp1d(
                freq,
                h[:, rx, tx] * edge,
                bounds_error=False,
                fill_value=(h[0, rx, tx].real, 0),
            )(fft_freq)
            data = np.roll(x, 31 * spui * tx)
            y += irfft(rfft(data) * hh, n=len(x))
        out.append(y)
    return np.array(out)


def eye(y, threshold):
    # Use three repeated periods to make all two-UI windows complete.
    y = np.tile(y, 3)
    t = np.arange(len(y)) * ui / spui
    cycles = np.arange(127, 254)
    a = np.interp((cycles[:, None] + np.arange(spui) / spui) * ui, t, y)
    heights = []
    for col in a.T:
        hi = col[col >= threshold]
        lo = col[col < threshold]
        heights.append(float(hi.min() - lo.max()) if len(hi) and len(lo) else 0)
    best = int(np.argmax(heights))
    i = np.where((y[:-1] - threshold) * (y[1:] - threshold) < 0)[0]
    cross = t[i] + (threshold - y[i]) * (t[i + 1] - t[i]) / (y[i + 1] - y[i])
    cross = cross[(cross >= 127 * ui) & (cross < 254 * ui)]
    ph = np.sort((cross / ui) % 1)
    width = float(np.diff(np.r_[ph, ph[0] + 1]).max()) if len(ph) else 0
    offset = (
        float(np.angle(np.mean(np.exp(2j * np.pi * ph))) / (2 * np.pi)) % 1
        if len(ph)
        else 0
    )
    traces = np.interp(
        (cycles[:, None] + np.arange(2 * spui) / spui + offset) * ui, t, y
    )
    return {
        "height_v": max(heights),
        "width_ui": width,
        "best_phase_ui": best / spui,
        "min_v": float(np.min(y)),
        "max_v": float(np.max(y)),
        "threshold_v": threshold,
        "bits": 127,
        "spui": spui,
    }, traces


def step_delay(h):
    n = 25600
    hf = np.zeros(n // 2 + 1, complex)
    hf[: len(freq)] = h * edge
    step = irfft(hf, n=n).cumsum()
    t = np.arange(n) / 1e7 / n
    target = h[0].real / 2
    inds = np.flatnonzero((step[:-1] < target) & (step[1:] >= target))
    if not len(inds):
        return None
    i = inds[0]
    return float(
        (
            t[i]
            + (target - step[i]) * (t[i + 1] - t[i]) / (step[i + 1] - step[i])
            - 5 * sigma
        )
        * 1e12
    )


def analyze(
    data_dir=ROOT / "data/cases", output_dir=ROOT / "build/reanalysis", refinement=4
):
    """Recompute metrics from native channels without changing recorded evidence."""
    base = Path(data_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir == base or base in output_dir.parents:
        raise ValueError("Write reanalysis outside the input evidence tree")
    results = {}
    for level in CASES:
        folder = base / level
        destination = output_dir / level
        destination.mkdir(parents=True, exist_ok=True)
        diff = "differential" in folder.name
        two = "two-channels" in folder.name
        our_folder = folder / "refinement4" if refinement == 4 else folder
        of, os = channel(
            next(our_folder.glob("our-channel.s*p")),
            reorder=[0, 2, 1, 3] if diff else None,
        )
        if two:
            ns = ["D0", "D1"]
            n0 = rf.Network(str(folder / "kisi/D0/D0.s2p"))
            kf = n0.f
            ks = np.zeros((len(kf), 4, 4), complex)
            dcf = None
            dcs = np.zeros((1, 4, 4), complex)
            for i, name in enumerate(ns):
                n = rf.Network(str(folder / f"kisi/{name}/{name}.s2p"))
                ks[:, 2 * i : 2 * i + 2, 2 * i : 2 * i + 2] = n.s
                dc = rf.Network(str(folder / f"kisi-dc/{name}/{name}.s2p"))
                dcs[:, 2 * i : 2 * i + 2, 2 * i : 2 * i + 2] = dc.s[:1]
                dcf = dc.f[0]
            kf = np.r_[dcf, kf]
            ks = np.concatenate([dcs, ks])
            notes = [
                "Kisi exports each lane independently; block-diagonal assembly deliberately contains no inter-lane coupling."
            ]
        else:
            name = "BUS_P" if diff else "DATA"
            ext = "s4p" if diff else "s2p"
            kf, ks = channel(
                folder / f"kisi/{name}/{name}.{ext}",
                folder / f"kisi-dc/{name}/{name}.{ext}",
            )
            notes = []
        if diff:
            notes += [
                "Original 120ohm resistor remains at its physical nodes in our circuit. Kisi removes it from the channel and applies it as an RX differential termination; the common loading restores that 120ohm bridge, without duplicating it. This includes a placement approximation in Kisi."
            ]
        oh = response(of, os, diff, False)
        kh = response(kf, ks, diff, diff)
        waves = {"our": periodic(oh), "kisi": periodic(kh)}
        threshold = float((oh[0, 0, 0].real + kh[0, 0, 0].real) / 4)
        metrics = {}
        eyes = {}
        for name, arr in waves.items():
            metrics[name] = []
            eyes[name] = []
            for y in arr:
                m, traces = eye(y, threshold)
                metrics[name].append(m)
                eyes[name].append(traces)
        delta = oh - kh
        result = {
            "level": folder.name,
            "signal_names": ["BUS_P-N"] if diff else ["D0", "D1"] if two else ["DATA"],
            "our": metrics["our"],
            "kisi": metrics["kisi"],
            "loaded_gain_1ghz_db": {
                "our": float(20 * np.log10(abs(oh[100, 0, 0]))),
                "kisi": float(20 * np.log10(abs(kh[100, 0, 0]))),
            },
            "step_delay_ps": {
                "our": step_delay(oh[:, 0, 0]),
                "kisi": step_delay(kh[:, 0, 0]),
            },
            "dc_gain_v_per_bit": {
                "our": float(oh[0, 0, 0].real),
                "kisi": float(kh[0, 0, 0].real),
            },
            "max_complex_loaded_difference_to_3ghz": float(
                abs(delta[freq <= 3e9]).max()
            ),
            "max_complex_loaded_difference_to_10ghz": float(abs(delta).max()),
            "kisi_max_singular_value": float(
                np.linalg.svd(ks, compute_uv=False)[:, 0].max()
            ),
            "notes": notes,
            "render_diagnostics": json.loads(
                (folder / "render-diagnostics.json").read_text()
            ),
            "kicad_shorts": [
                v
                for v in json.loads((folder / "kicad-drc.json").read_text())[
                    "violations"
                ]
                if v["type"] == "shorting_items"
            ],
        }
        if two:
            result["our_cross_transfer_peak_v_per_bit"] = float(
                abs(oh[:, 1, 0] * edge).max()
            )
        np.savez_compressed(
            destination / "comparison.npz",
            frequency=freq,
            our_h=oh,
            kisi_h=kh,
            our_eye=eyes["our"],
            kisi_eye=eyes["kisi"],
            our_voltage=waves["our"],
            kisi_voltage=waves["kisi"],
        )
        (destination / "comparison.json").write_text(json.dumps(result, indent=2))
        results[folder.name] = result
        print(
            f"{folder.name}: eye {metrics['our'][0]['height_v']:.6f} / {metrics['kisi'][0]['height_v']:.6f} V; delay {result['step_delay_ps']['our']:.2f} / {result['step_delay_ps']['kisi']:.2f} ps",
            flush=True,
        )
    summary = {
        "settings": {
            "our_spatial_refinement": refinement,
            "bitrate_bps": 1e9,
            "prbs": 7,
            "spui": spui,
            "edge_10_90_ps": 100,
            "source_ohm_per_leg": 50,
            "pin_capacitance_pf_per_leg": 1,
            "single_ended_rx_ohm": 50,
            "differential_rx_bridge_ohm": 120,
            "noise": 0,
            "jitter": 0,
            "equalization": False,
            "two_channel_pattern_offset_ui": 31,
            "roughness": "smooth",
            "native_touchstone_used_for_kisi": True,
            "native_ngspice_ac_used_for_ours": True,
            "eye_processing": "Same FFT and metric implementation for both independent extracted channels; no output amplitude normalization.",
        },
        "examples": results,
    }
    (output_dir / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
