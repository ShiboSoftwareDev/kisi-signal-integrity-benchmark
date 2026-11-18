Board `board.kicad_pcb`. ngspice: ** ngspice-47 : Circuit level simulation program.

| lane | model | length mm | elements (R/L/C/src) | ngspice vs kisi: |ΔS21| dB to 1.5×Nyq / to fmax | max |ΔS| to 1.5×Nyq / all | kisi's own evaluation: max |ΔS| | step: max diff, t50 ngspice / kisi (ps) | largest singular value: kisi to 10×fmax / ngspice sweep |
|---|---|---|---|---|---|---|---|---|
| BUS_P | 4-port (pair), ladder | 55.8 | 2218/1586/992/80 | 0.099 / 3.38 | 0.016 / 0.443 | 0.443 | 5.18 %, 346.2 / 338.1 | 0.999998 / 1.000000 |
| BUS_P | 4-port (pair), compact | 55.8 | 714/771/627/80 | 0.100 / 3.41 | 0.016 / 0.451 | 0.451 | 5.21 %, 346.2 / 338.1 | 0.999998 / 1.000000 |

| lane | elements ladder / compact | compact vs ladder (ngspice): |ΔS21| dB to 1.5×Nyq / fmax | max |ΔS| to 1.5×Nyq / fmax | step diff | PRBS levels: max diff (of swing) | ngspice S-par. s ladder / compact | ngspice bench s ladder / compact |
|---|---|---|---|---|---|---|---|
| BUS_P | 4876 / 2192 | 0.0004 / 0.172 | 0.0001 / 0.0295 | 0.17 % | 0.30 mV (0.08 %) | 2.5 / 0.1 | 101.2 / 2.3 |
