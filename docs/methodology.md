# Methodology

## Inputs and independent extraction

The three examples are `level1-single-ended`, `level1-differential`, and `level2-two-channels` at pipeline commit `374229d3dd3ca4581053423604b715dfb11ac86b`. The source audit checked 360 archive files without finding modifications. Published dependencies are core 0.0.2409, props 0.0.735, and circuit-json 0.0.552, installed with pnpm 11.25.0 and the frozen upstream lockfile.

Fresh tscircuit renders supply the physical records. The pipeline’s native routed network supplies one channel; Kisi independently extracts a translation into KiCad. The translator preserves routes, pads, vias, copper pours, and the generated stackup. It changes coordinate handedness/origin and conventional reference/net names, without repairing routing. The generated stack totals 1.49 mm (30 µm copper / 1.43 mm core / 30 µm copper), although TSX specifies a nominal 1.6 mm board.

Both use explicit assumptions of 20 µm mask, mask εr 3.3 and tanδ 0.025, laminate tanδ 0.02, smooth copper, and 58 MS/m conductivity. These are assumptions, not measured material data.

The pipeline native network retains all top-level linear R/L/C/K/G/E/F/H/V primitives, including controlled coupling/loss sources. IBIS subcircuits and packages are excluded from the common linear comparison. Declared supplies become AC ground references. ngspice excites each port with a 2 V source behind 50 Ω and terminates the remaining ports through 50 Ω. The port voltages give Sij; subtract one from the driven diagonal. The final network uses spatial refinement 4, with refinement 2 retained for convergence comparisons.

Kisi 0.3.3 supplies its native Touchstone output. Its fitted SPICE export is checked separately. `KISI_THREADS=1` is an upstream-supported runtime setting; the release CLI hash and validator source hash are pinned. No solver physics is patched.

## Loading and port order

Both native S matrices use 50 Ω reference impedances. Convert to admittance using Y = (I + S)⁻¹(I − S) / 50, add the explicit shunt/source admittances, and solve the node voltages. Source strength is 2 V open circuit for single-ended signals and ±1 V on differential legs. Add 1 pF per endpoint/leg.

Pipeline single-ended port pairs are `[D0_in, D0_out, D1_in, D1_out]`. Reorder the pipeline differential ports from `[P_in, P_out, N_in, N_out]` to Kisi’s `[P_in, N_in, P_out, N_out]`. The differential output is P_out minus N_out.

Single-ended RX termination is 50 Ω. The differential board has a 120 Ω resistor near the RX pads; the pipeline retains that resistor at its physical nodes. Kisi removes it from the channel and represents it at the RX reference. The common loading adds the 120 Ω bridge to Kisi only. That placement approximation is explicit. It produces a nominal differential received swing near 1.091 V; no gain normalization makes it look like a 1 V eye.

Kisi exports D0 and D1 separately. Their two-port matrices are assembled as a block diagonal four-port matrix, which contains no inter-lane coupling. The pipeline retains coupling. The original board’s physical short invalidates a physical crosstalk conclusion from this case.

## Waveforms and metrics

Use a 1 Gbps PRBS7 period of 127 bits, with 256 samples/UI. The second lane’s pattern is offset by 31 UI. The Gaussian edge has 100 ps 10–90% duration, σ = 100 ps / 2.5631031310892007. A 5σ artificial delay makes its frequency representation causal. Noise, jitter, and equalization are absent.

Interpolate the loaded native response onto 0–10 GHz with 10 MHz spacing. Kisi’s additional near-DC export supplies its low-frequency anchor. The zero-frequency value is the real part of that near-DC response, without amplitude rescaling. FFT multiplication synthesizes a periodic steady-state waveform; three copies provide complete eye windows.

Eye height is the maximum, across sampled phases, of minimum high voltage minus maximum low voltage. A common threshold is one quarter of the sum of the tools’ DC bit swings. An independent known-PRBS-label classification reproduces all eight height measurements on the same absolute phase grid. Width is the largest circular gap in interpolated threshold-crossing phases. Plots align traces to the circular mean crossing phase; that display alignment does not remove timing from the delay metric.

Loaded step delay is the interpolated first upward 50% crossing of the loaded step, with the artificial 5σ delay removed. The padded inverse transform has 25,600 samples. Reported delay belongs to the loaded circuit, not simply copper propagation.

Kisi’s native profile checker uses normalized eye height and a different width metric. Those values remain separate from the common absolute-voltage measurements.

## Qualification

The 1 Gbps comparison is a linear channel stress test, not a nonlinear IBIS or interface compliance test. Separate original-rate 16-bit IBIS runs shorten recording duration only and preserve PCB records; they remain `candidate-unqualified`. The shorted case is blocked before that native IBIS run.

Spatial 2→4 refinement bounds one numerical sensitivity. It does not establish field-mesh convergence or physical sign-off. Passivity, reciprocity, agreement between two tools, and successful CI likewise do not establish physical truth. The current differential and two-channel board identities differ from historical accepted captures, so no historical bitwise replay is claimed.
