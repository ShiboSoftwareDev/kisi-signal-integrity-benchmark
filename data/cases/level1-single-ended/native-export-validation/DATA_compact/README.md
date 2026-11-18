# kisi export: lane DATA

kisi 0.3.3 – board `board.kicad_pcb`. The lane's board channel as kisi's channel check models it, for circuit and RF simulators.

## Ports

| port | node | on the board |
|---|---|---|
| 1 | `a` | DATA at U1.4 (transmitter end) |
| 2 | `b` | DATA at U2.2 (receiver end) |
| – | `ref` | reference (ground); connect to node 0 |

Reference impedance 50.00 Ω per port. Track length 28.12 mm, delay 162.1 ps.

## Files

* `DATA.lib` – the lane as SPICE subcircuit `DATA_lane` (plain R, L, C, E, F, V elements: ngspice, Xyce, LTspice, KiCad). One subcircuit per line section, via, part and stub; the lane subcircuit last.
* `bench_ngspice.cir` – transient test bench (PRBS7, the profile's linear ends): `ngspice -b bench_ngspice.cir` writes `bench_ngspice.txt` (time, receiver voltage).
* `sparam_ngspice.cir` – S-parameter analysis on kisi's frequency grid: `ngspice -b sparam_ngspice.cir` writes `sparam_ngspice.txt` (S_i_j for i, j = 1…2).
* `bench_xyce.cir`, `sparam_xyce.cir` – the same for Xyce (`.print tran` to CSV; `.lin` writes `sparam_xyce.s2p`).
* `bench_ltspice.cir`, `DATA_ltspice.lib`, `sparam_ltspice.cir` – the bench for LTspice (see below).
* `DATA.s2p` – kisi's S-parameters of the same channel (Touchstone 1.0, RI) for RF tools (scikit-rf, PyBERT, Qucs-S/Qucsator).
* `DATA.kicad_pro`, `DATA.kicad_sch`, `DATA_kicad.lib`, `kisi.kicad_sym`, `sym-lib-table` – a KiCad simulation project (with kisi's symbols as a project library): the lane's elements as symbols, the PRBS7 sources and the linear ends as R, L, C symbols, a `.tran` directive. Open it, then Inspect → Simulator → Run, and probe the receiver die.

## ngspice and Xyce

The circuit, `DATA.lib`, is the same for both. Only the small decks around it differ, because the two simulators define ports and write results differently:

* ngspice: results from a `.control` block (`run`, then `wrdata` to a text file); S-parameters with `.sp` and voltage sources marked `portnum N z0 Z`.
* Xyce: results with `.print … format=csv` and, for S-parameters, port devices `P… port=N z0=Z` with `.ac` and `.lin sparcalc=1` (written as Touchstone).

One deck for both does not work without editing: ngspice reads a `P` line as its coupled-line device and has no `.lin`, Xyce knows neither `portnum` nor `.control` scripts, and both read `*` only as a comment – a commented-out dialect would have to be switched by hand. Hence one deck per simulator and analysis.

## LTspice

Open `bench_ltspice.cir` in LTspice (File → Open, files of type netlist) and run it. It is the transient bench of the other simulators – the same PRBS7 PWL source, the profile's linear ends, the lane subcircuit – with the received voltage as node `vrx` (a pair: V(P) − V(N), a B source) and `.meas` lines whose results LTspice writes to the `.log` file (View → SPICE Error Log): the first rising zero crossing `t50`, the voltage at eight bit centres of the second pattern period and its extremes there. `.options plotwinsize=0 numdgt=16 reject_number_tails` keeps the waveform uncompressed and in double precision in the `.raw` file and makes LTspice report a number with stray letters instead of ignoring them; every value is written in e-notation (in LTspice `1M` would be milli).

* `DATA_ltspice.lib` is `DATA.lib` with `Rser=0 Rpar=1e30` on every inductor: LTspice adds a series resistance (1 mΩ) and an implicit parallel damping to inductors by default; the LTspice library sets Rser=0 and Rpar=1e30 so that it matches ngspice and Xyce, which do not accept these parameters. Otherwise the two files are the same circuit (`validation/channel_export/ltspice.py check` in the kisi repository verifies it).
* `sparam_ltspice.cir`: S-parameters with LTspice's `.net` analysis (the source's `Rser` and `Rout` are the port impedances); plot `S21(Vin)` and `S11(Vin)`.
* Not tested in LTspice by kisi (LTspice runs on Windows and macOS only): the files follow LTspice's syntax and are checked for it; ngspice runs the same bench and gives the reference numbers.

## KiCad

The sheet shows the lane subcircuit `DATA_lane` element by element, in its order: TL line sections (consecutive sections of one line on one layer as one), CPL coupled runs spanning the P and N rows, VIA and VP vias and via pairs, the board's parts (e.g. C40) with their parasitics, CP pad capacitances (also of unfitted parts), ST and SP open stubs. A long lane wraps into several rows.

* Each symbol has `Sim.Device = SUBCKT`, `Sim.Library = DATA_kicad.lib` and `Sim.Name = <element>_k`: a wrapper that calls the element's subcircuit in `DATA.lib` with its reference node on ground. KiCad reads the models from the file `Sim.Library` names, so the wrappers keep that file short; its `.include` brings in the lane library for the simulator.
* A part's Value is its subcircuit parameter (`Sim.Params = c=${VALUE}`, or `r=`/`l=`): edit the Value in SPICE notation (100n, 4.7u, 1k, 1Meg) and the parasitics kisi uses (ESR, ESL, estimates) stay. An inductor's parameter is its total inductance (ESL included). Pads keep fixed values.
* `kisi export --kicad-style compact` writes the lane as one symbol instead.
* File format: KiCad 7 (version 20230121), which KiCad 7, 8 and 9 open (they convert it when saving). Checked in kisi's repository with kicad-cli: the netlist equals the lane subcircuit node for node, its AC response in ngspice equals the bench's, every pin and wire end is connected, and KiCad's ERC (kicad-cli 8 and later) reports no unconnected pin or dangling wire. Not tested: the simulator dialog of the KiCad GUI.

## Test bench ends (per line)

Profile `se50`: 1.000 Gbit/s, edge 100.0 ps (10–90 %), the receiver sees ±1.000 V at DC.

Transmitter (single-ended): profile se50, 1.000 Gbit/s, PRBS7, edge 100.0 ps (10-90 %). Thevenin source: emf ±2.000 V behind R 50.00 Ω, C 1.000 pF at the die. A voltage-mode driver with 50.00 Ω source resistance. The emf is scaled so that the receiver sees ±1.000 V at DC.

Receiver (single-ended): R 50.00 Ω and C 1.000 pF from the die to ground. Probe the die node (top of CRX/RRX).

* transmitter: emf → R 50.00 Ω → die (C 1.000 pF to ground) → L 0 nH → port
* receiver: port → L 0 nH → die: C 1.000 pF and R 50.00 Ω to ground

## Model

* Line sections (compact model, `--model compact`): the same fitted networks as the ladder – a Foster network (R0 + L + R‖L terms) for the conductor impedance R(f) + jωL(f) and a Debye network (C + R–C branches) for the dielectric admittance G(f) + jωC(f), fitted to kisi's line model with positive elements only – but written as lossless-line cells: a lossless LC ladder with the fits' L and C (40 π sections per wavelength at the top frequency: the delay, within 0.1 % in phase there) and the rest of both networks lumped once per cell, at least 3 cells per (delay × top frequency), more where the lumped losses are large (microstrip). Every element is a positive R, L or C: passive and causal by construction. Consecutive sections of one line on one layer with nearly the same model are merged into one (the length-weighted mean of their R(f), L(f), G(f), C(f)).
* The cells' lumped losses reflect coherently from about 1.5 × the top frequency (15.00 GHz) on: above the top frequency the model is not meant to be used.
* Vias: kisi's via model – the physics-based ladder (node capacitances, plane-pair impedances, open barrel stubs, junction inductances) or the coaxial section stack. The via models run from via centre to via centre; the feed trace they remove or add is taken from the neighbouring line sections.
* Parts (series and shunt) with the parasitics kisi uses (estimates from `data/components.json`); open stubs as their own chain. A series capacitor has 1 GΩ across it (a DC path for the simulator).

Check against kisi's own S-parameters of this channel (the circuit evaluated in kisi): up to 1.5 × Nyquist |ΔS21| ≤ 0.005129 dB and the largest difference of any S-parameter 0.0006898; up to 10.00 GHz 0.4545 dB and 0.1747. Fits of the main line sections (each at least 10 % of the length): R(f) within 0.5148 %, X(f) 0.01713 %, G(f) 17.43 %, B(f) 3.524 %; via ladders 0 %. `validation/channel_export/` in the kisi repository runs these files in ngspice and compares.

Why it is not exact: kisi's roughness adds resistance without its internal inductance, the via models use a constant loss tangent and a barrel resistance without internal inductance, and some via spans have a negative resistance at high frequency – a passive, causal circuit cannot follow those exactly; the fits keep the loss and, closer, the reactance (the delay).

Elements after flattening: 144 R, 158 L, 136 C, 0 controlled sources and probes; 0 RLGC sections, 11 lossless-line cells. The circuit's largest singular value of S from 1 kHz to 10 × the top frequency: 0.999999 (passive: ≤ 1).

## Not included

* The receiver's termination resistors on the board: they act as the receiver's termination (bench and Touchstone leave them out, as kisi's eye does).
* The channel behind a connector, crosstalk from other lanes (kisi's coupling scan is separate), non-linear buffers: IBIS (KiCad's KIBIS) ends need `kisi.json` IBIS models – not part of this export yet; replace the source and the receiver in the KiCad schematic by KiCad's IBIS symbols by hand.

## Stackup

```text
stackup used (2 copper layers, 1.49 mm; er and tand at 1 GHz, the line models follow Djordjevic-Sarkar from there):
  solder mask (top): 20 um, er 3.3 [board file]
  F.Cu: copper 30 um [board file]
    NP-155F core: 1430 um, er 4.42, tand 0.02 [board file]
  B.Cu: copper 30 um [board file]
  solder mask (bottom): 20 um, er 3.3 [board file]
```
