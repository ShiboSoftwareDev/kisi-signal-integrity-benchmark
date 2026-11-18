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
* `BUS_P.s4p` – kisi's S-parameters of the same channel (Touchstone 1.0, RI) for RF tools (scikit-rf, PyBERT, Qucs-S/Qucsator).

## Test bench ends (per line)

Profile `lvds`: 1.000 Gbit/s, edge 300.0 ps (10–90 %), the receiver sees ±0.3500 V at DC (differential).

Transmitter (per line, P and N in opposite phase): profile lvds, 1.000 Gbit/s, PRBS7, edge 300.0 ps (10-90 %). Thevenin source: emf ±14.76 V behind R 5000 Ω, C 2.000 pF at the die. R ≫ the receiver's 60.00 Ω: a current-mode driver as its Thevenin equivalent, I = emf/(R + 60.00 Ω) = 2.917 mA per line. The emf is scaled so that the receiver sees ±0.3500 V at DC differential.

Receiver (per line): R 60.00 Ω and C 2.000 pF from the die to ground. A 120.0 Ω differential termination, split into two halves to the reference. Probe the die nodes (top of CRX/RRX): V(P) − V(N).

* transmitter: emf → R 5000 Ω → die (C 2.000 pF to ground) → L 0 nH → port
* receiver: port → L 0 nH → die: C 2.000 pF and R 60.00 Ω to ground
* termination R1 at U2 used as the receiver termination (60 Ω per line)

## Model

* Line sections (compact model, `--model compact`): the same fitted networks as the ladder – a Foster network (R0 + L + R‖L terms) for the conductor impedance R(f) + jωL(f) and a Debye network (C + R–C branches) for the dielectric admittance G(f) + jωC(f), fitted to kisi's line model with positive elements only – but written as lossless-line cells: a lossless LC ladder with the fits' L and C (40 π sections per wavelength at the top frequency: the delay, within 0.1 % in phase there) and the rest of both networks lumped once per cell, at least 3 cells per (delay × top frequency), more where the lumped losses are large (microstrip). Every element is a positive R, L or C: passive and causal by construction. Consecutive sections of one line on one layer with nearly the same model are merged into one (the length-weighted mean of their R(f), L(f), G(f), C(f)).
* The cells' lumped losses reflect coherently from about 1.5 × the top frequency (15.00 GHz) on: above the top frequency the model is not meant to be used.
* Vias: kisi's via model – the physics-based ladder (node capacitances, plane-pair impedances, open barrel stubs, junction inductances) or the coaxial section stack. The via models run from via centre to via centre; the feed trace they remove or add is taken from the neighbouring line sections.
* Parts (series and shunt) with the parasitics kisi uses (estimates from `data/components.json`); open stubs as their own chain. A series capacitor has 1 GΩ across it (a DC path for the simulator).
* Pair: both lines on their own paths; coupled runs, via pairs and stub pairs as modal blocks – even- and odd-mode chains between ideal mode converters (E and F sources: V_e = (V_P + V_N)/2, V_o = (V_P − V_N)/2, I_P = I_e + I_o, I_N = I_e − I_o), as kisi computes them. Differential and common mode, mode conversion and skew are included.

Check against kisi's own S-parameters of this channel (the circuit evaluated in kisi): up to 1.5 × Nyquist |ΔS21| ≤ 0.09985 dB and the largest difference of any S-parameter 0.01595; up to 10.00 GHz 3.411 dB and 0.4511. Fits of the main line sections (each at least 10 % of the length): R(f) within 0.5976 %, X(f) 0.04508 %, G(f) 95.98 %, B(f) 13.31 %; via ladders 0 %. `validation/channel_export/` in the kisi repository runs these files in ngspice and compares.

Why it is not exact: kisi's roughness adds resistance without its internal inductance, the via models use a constant loss tangent and a barrel resistance without internal inductance, and some via spans have a negative resistance at high frequency – a passive, causal circuit cannot follow those exactly; the fits keep the loss and, closer, the reactance (the delay).

Elements after flattening: 714 R, 771 L, 627 C, 80 controlled sources and probes; 0 RLGC sections, 56 lossless-line cells. The circuit's largest singular value of S from 1 kHz to 10 × the top frequency: 0.999998 (passive: ≤ 1).

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
