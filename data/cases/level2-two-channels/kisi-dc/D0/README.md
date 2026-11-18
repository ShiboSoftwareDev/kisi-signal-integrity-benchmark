# kisi export: lane D0

kisi 0.3.3 – board `board.kicad_pcb`. The lane's board channel as kisi's channel check models it, for circuit and RF simulators.

## Ports

| port | node | on the board |
|---|---|---|
| 1 | `a` | D0 at U1.4 (transmitter end) |
| 2 | `b` | D0 at U3.2 (receiver end) |
| – | `ref` | reference (ground); connect to node 0 |

Reference impedance 50.00 Ω per port. Track length 28.12 mm, delay 162.1 ps.

## Files

* `D0.s2p` – kisi's S-parameters of the same channel (Touchstone 1.0, RI) for RF tools (scikit-rf, PyBERT, Qucs-S/Qucsator).

## Test bench ends (per line)

Profile `se50`: 1.000 Gbit/s, edge 100.0 ps (10–90 %), the receiver sees ±1.000 V at DC.

Transmitter (single-ended): profile se50, 1.000 Gbit/s, PRBS7, edge 100.0 ps (10-90 %). Thevenin source: emf ±2.000 V behind R 50.00 Ω, C 1.000 pF at the die. A voltage-mode driver with 50.00 Ω source resistance. The emf is scaled so that the receiver sees ±1.000 V at DC.

Receiver (single-ended): R 50.00 Ω and C 1.000 pF from the die to ground. Probe the die node (top of CRX/RRX).

* transmitter: emf → R 50.00 Ω → die (C 1.000 pF to ground) → L 0 nH → port
* receiver: port → L 0 nH → die: C 1.000 pF and R 50.00 Ω to ground

## Model

* Line sections (compact model, `--model compact`): the same fitted networks as the ladder – a Foster network (R0 + L + R‖L terms) for the conductor impedance R(f) + jωL(f) and a Debye network (C + R–C branches) for the dielectric admittance G(f) + jωC(f), fitted to kisi's line model with positive elements only – but written as lossless-line cells: a lossless LC ladder with the fits' L and C (40 π sections per wavelength at the top frequency: the delay, within 0.1 % in phase there) and the rest of both networks lumped once per cell, at least 3 cells per (delay × top frequency), more where the lumped losses are large (microstrip). Every element is a positive R, L or C: passive and causal by construction. Consecutive sections of one line on one layer with nearly the same model are merged into one (the length-weighted mean of their R(f), L(f), G(f), C(f)).
* The cells' lumped losses reflect coherently from about 1.5 × the top frequency (1.875 GHz) on: above the top frequency the model is not meant to be used.
* Vias: kisi's via model – the physics-based ladder (node capacitances, plane-pair impedances, open barrel stubs, junction inductances) or the coaxial section stack. The via models run from via centre to via centre; the feed trace they remove or add is taken from the neighbouring line sections.
* Parts (series and shunt) with the parasitics kisi uses (estimates from `data/components.json`); open stubs as their own chain. A series capacitor has 1 GΩ across it (a DC path for the simulator).

Check against kisi's own S-parameters of this channel (the circuit evaluated in kisi): up to 1.5 × Nyquist |ΔS21| ≤ 0.003383 dB and the largest difference of any S-parameter 0.0003748; up to 1.250 GHz 0.01070 dB and 0.001483. Fits of the main line sections (each at least 10 % of the length): R(f) within 0.6348 %, X(f) 0.05562 %, G(f) 0.7348 %, B(f) 0.01269 %; via ladders 0 %. `validation/channel_export/` in the kisi repository runs these files in ngspice and compares.

Why it is not exact: kisi's roughness adds resistance without its internal inductance, the via models use a constant loss tangent and a barrel resistance without internal inductance, and some via spans have a negative resistance at high frequency – a passive, causal circuit cannot follow those exactly; the fits keep the loss and, closer, the reactance (the delay).

Elements after flattening: 53 R, 35 L, 46 C, 0 controlled sources and probes; 0 RLGC sections, 3 lossless-line cells. The circuit's largest singular value of S from 1 kHz to 10 × the top frequency: 0.999999 (passive: ≤ 1).

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
