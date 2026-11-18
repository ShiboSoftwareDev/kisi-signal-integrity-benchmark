# kisi export: lane BUS_P

kisi 0.3.3 – board `board.kicad_pcb`. The lane's board channel as kisi's channel check models it, for circuit and RF simulators.

## Ports

| port | node | on the board |
|---|---|---|
| 1 | `ap` | P BUS_P at U1.6 (transmitter end) |
| 2 | `an` | N BUS_N at U1.7 (transmitter end) |
| 3 | `bp` | P BUS_P at U2.6 (receiver end) |
| 4 | `bn` | N BUS_N at U2.7 (receiver end) |
| – | `ref` | reference (ground); connect to node 0 |

Reference impedance 50.00 Ω per port (100.0 Ω differential). Track length 55.75 mm, delay 315.3 ps.

## Files

* `BUS_P.lib` – the lane as SPICE subcircuit `BUS_P_lane` (plain R, L, C, E, F, V elements: ngspice, Xyce, LTspice, KiCad). One subcircuit per line section, via, part and stub; the lane subcircuit last.
* `bench_ngspice.cir` – transient test bench (PRBS7, the profile's linear ends): `ngspice -b bench_ngspice.cir` writes `bench_ngspice.txt` (time, receiver voltage).
* `sparam_ngspice.cir` – S-parameter analysis on kisi's frequency grid: `ngspice -b sparam_ngspice.cir` writes `sparam_ngspice.txt` (S_i_j for i, j = 1…4).
* `bench_xyce.cir`, `sparam_xyce.cir` – the same for Xyce (`.print tran` to CSV; `.lin` writes `sparam_xyce.s4p`).
* `bench_ltspice.cir`, `BUS_P_ltspice.lib` – the bench for LTspice (see below).
* `BUS_P.s4p` – kisi's S-parameters of the same channel (Touchstone 1.0, RI) for RF tools (scikit-rf, PyBERT, Qucs-S/Qucsator).
* `BUS_P.kicad_pro`, `BUS_P.kicad_sch`, `BUS_P_kicad.lib`, `kisi.kicad_sym`, `sym-lib-table` – a KiCad simulation project (with kisi's symbols as a project library): the lane's elements as symbols, the PRBS7 sources and the linear ends as R, L, C symbols, a `.tran` directive. Open it, then Inspect → Simulator → Run, and probe the receiver die.

## ngspice and Xyce

The circuit, `BUS_P.lib`, is the same for both. Only the small decks around it differ, because the two simulators define ports and write results differently:

* ngspice: results from a `.control` block (`run`, then `wrdata` to a text file); S-parameters with `.sp` and voltage sources marked `portnum N z0 Z`.
* Xyce: results with `.print … format=csv` and, for S-parameters, port devices `P… port=N z0=Z` with `.ac` and `.lin sparcalc=1` (written as Touchstone).

One deck for both does not work without editing: ngspice reads a `P` line as its coupled-line device and has no `.lin`, Xyce knows neither `portnum` nor `.control` scripts, and both read `*` only as a comment – a commented-out dialect would have to be switched by hand. Hence one deck per simulator and analysis.

## LTspice

Open `bench_ltspice.cir` in LTspice (File → Open, files of type netlist) and run it. It is the transient bench of the other simulators – the same PRBS7 PWL source, the profile's linear ends, the lane subcircuit – with the received voltage as node `vrx` (a pair: V(P) − V(N), a B source) and `.meas` lines whose results LTspice writes to the `.log` file (View → SPICE Error Log): the first rising zero crossing `t50`, the voltage at eight bit centres of the second pattern period and its extremes there. `.options plotwinsize=0 numdgt=16 reject_number_tails` keeps the waveform uncompressed and in double precision in the `.raw` file and makes LTspice report a number with stray letters instead of ignoring them; every value is written in e-notation (in LTspice `1M` would be milli).

* `BUS_P_ltspice.lib` is `BUS_P.lib` with `Rser=0 Rpar=1e30` on every inductor: LTspice adds a series resistance (1 mΩ) and an implicit parallel damping to inductors by default; the LTspice library sets Rser=0 and Rpar=1e30 so that it matches ngspice and Xyce, which do not accept these parameters. Otherwise the two files are the same circuit (`validation/channel_export/ltspice.py check` in the kisi repository verifies it).
* LTspice's `.net` analysis is a two-port one; it has no N-port S-parameters, so for a pair or a bus use the Touchstone file `BUS_P.s4p`.
* Not tested in LTspice by kisi (LTspice runs on Windows and macOS only): the files follow LTspice's syntax and are checked for it; ngspice runs the same bench and gives the reference numbers.

## KiCad

The sheet shows the lane subcircuit `BUS_P_lane` element by element, in its order: TL line sections (consecutive sections of one line on one layer as one), CPL coupled runs spanning the P and N rows, VIA and VP vias and via pairs, the board's parts (e.g. C40) with their parasitics, CP pad capacitances (also of unfitted parts), ST and SP open stubs. A long lane wraps into several rows.

* Each symbol has `Sim.Device = SUBCKT`, `Sim.Library = BUS_P_kicad.lib` and `Sim.Name = <element>_k`: a wrapper that calls the element's subcircuit in `BUS_P.lib` with its reference node on ground. KiCad reads the models from the file `Sim.Library` names, so the wrappers keep that file short; its `.include` brings in the lane library for the simulator.
* A part's Value is its subcircuit parameter (`Sim.Params = c=${VALUE}`, or `r=`/`l=`): edit the Value in SPICE notation (100n, 4.7u, 1k, 1Meg) and the parasitics kisi uses (ESR, ESL, estimates) stay. An inductor's parameter is its total inductance (ESL included). Pads keep fixed values.
* `kisi export --kicad-style compact` writes the lane as one symbol instead.
* File format: KiCad 7 (version 20230121), which KiCad 7, 8 and 9 open (they convert it when saving). Checked in kisi's repository with kicad-cli: the netlist equals the lane subcircuit node for node, its AC response in ngspice equals the bench's, every pin and wire end is connected, and KiCad's ERC (kicad-cli 8 and later) reports no unconnected pin or dangling wire. Not tested: the simulator dialog of the KiCad GUI.

## Test bench ends (per line)

Profile `lvds`: 1.000 Gbit/s, edge 300.0 ps (10–90 %), the receiver sees ±0.3500 V at DC (differential).

Transmitter (per line, P and N in opposite phase): profile lvds, 1.000 Gbit/s, PRBS7, edge 300.0 ps (10-90 %). Thevenin source: emf ±14.76 V behind R 5000 Ω, C 2.000 pF at the die. R ≫ the receiver's 60.00 Ω: a current-mode driver as its Thevenin equivalent, I = emf/(R + 60.00 Ω) = 2.917 mA per line. The emf is scaled so that the receiver sees ±0.3500 V at DC differential.

Receiver (per line): R 60.00 Ω and C 2.000 pF from the die to ground. A 120.0 Ω differential termination, split into two halves to the reference. Probe the die nodes (top of CRX/RRX): V(P) − V(N).

* transmitter: emf → R 5000 Ω → die (C 2.000 pF to ground) → L 0 nH → port
* receiver: port → L 0 nH → die: C 2.000 pF and R 60.00 Ω to ground
* termination R1 at U2 used as the receiver termination (60 Ω per line)

## Model

* Line sections: RLGC ladders of π sections (at least the number per wavelength at the top frequency given in the library header); per section the external inductance, a Foster network (R0 + R‖L terms) for the conductor impedance R(f) + jωL_int(f) and a Debye network (C + R–C branches) for the dielectric admittance G(f) + jωC(f), fitted to kisi's line model (skin effect, Huray roughness, Djordjevic-Sarkar) with positive elements only – passive and causal by construction.
* Vias: kisi's via model – the physics-based ladder (node capacitances, plane-pair impedances, open barrel stubs, junction inductances) or the coaxial section stack. The via models run from via centre to via centre; the feed trace they remove or add is taken from the neighbouring line sections.
* Parts (series and shunt) with the parasitics kisi uses (estimates from `data/components.json`); open stubs as their own chain. A series capacitor has 1 GΩ across it (a DC path for the simulator).
* Pair: both lines on their own paths; coupled runs, via pairs and stub pairs as modal blocks – even- and odd-mode chains between ideal mode converters (E and F sources: V_e = (V_P + V_N)/2, V_o = (V_P − V_N)/2, I_P = I_e + I_o, I_N = I_e − I_o), as kisi computes them. Differential and common mode, mode conversion and skew are included.

Check against kisi's own S-parameters of this channel (the circuit evaluated in kisi): up to 1.5 × Nyquist |ΔS21| ≤ 0.09911 dB and the largest difference of any S-parameter 0.01564; up to 10.00 GHz 3.383 dB and 0.4426. Fits of the main line sections (each at least 10 % of the length): R(f) within 0.5148 %, X(f) 0.03238 %, G(f) 95.98 %, B(f) 13.31 %; via ladders 0 %. `validation/channel_export/` in the kisi repository runs these files in ngspice and compares.

Why it is not exact: kisi's roughness adds resistance without its internal inductance, the via models use a constant loss tangent and a barrel resistance without internal inductance, and some via spans have a negative resistance at high frequency – a passive, causal circuit cannot follow those exactly; the fits keep the loss and, closer, the reactance (the delay).

Elements after flattening: 2218 R, 1586 L, 992 C, 80 controlled sources and probes; 164 RLGC sections. The circuit's largest singular value of S from 1 kHz to 10 × the top frequency: 0.999998 (passive: ≤ 1).

## Not included

* The receiver's termination resistors on the board: they act as the receiver's termination (bench and Touchstone leave them out, as kisi's eye does).
* The channel behind a connector, crosstalk from other lanes (kisi's coupling scan is separate), non-linear buffers: IBIS (KiCad's KIBIS) ends need `kisi.json` IBIS models – not part of this export yet; replace the source and the receiver in the KiCad schematic by KiCad's IBIS symbols by hand.

## Notes from kisi's model

* termination R1 at U2 used as the receiver termination (60 Ω per line)
* BUS_P branches: 1 side stub(s) included as open stubs
* BUS_N branches: 1 side stub(s) included as open stubs

## Stackup

```text
stackup used (2 copper layers, 1.49 mm; er and tand at 1 GHz, the line models follow Djordjevic-Sarkar from there):
  solder mask (top): 20 um, er 3.3 [board file]
  F.Cu: copper 30 um [board file]
    NP-155F core: 1430 um, er 4.42, tand 0.02 [board file]
  B.Cu: copper 30 um [board file]
  solder mask (bottom): 20 um, er 3.3 [board file]
```
