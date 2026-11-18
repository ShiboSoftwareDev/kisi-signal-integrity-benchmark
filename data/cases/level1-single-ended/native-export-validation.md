Board `board.kicad_pcb`. ngspice: ** ngspice-47 : Circuit level simulation program.

| lane | model | length mm | elements (R/L/C/src) | ngspice vs kisi: |ΔS21| dB to 1.5×Nyq / to fmax | max |ΔS| to 1.5×Nyq / all | kisi's own evaluation: max |ΔS| | step: max diff, t50 ngspice / kisi (ps) | largest singular value: kisi to 10×fmax / ngspice sweep |
|---|---|---|---|---|---|---|---|---|
| DATA | 2-port, ladder | 28.1 | 483/329/232/0 | 0.005 / 0.44 | 0.001 / 0.153 | 0.153 | 2.94 %, 180.1 / 175.5 | 0.999999 / 1.000000 |
| DATA | 2-port, compact | 28.1 | 144/158/136/0 | 0.005 / 0.45 | 0.001 / 0.175 | 0.175 | 2.93 %, 180.1 / 175.5 | 0.999999 / 1.000000 |

| lane | elements ladder / compact | compact vs ladder (ngspice): |ΔS21| dB to 1.5×Nyq / fmax | max |ΔS| to 1.5×Nyq / fmax | step diff | PRBS levels: max diff (of swing) | ngspice S-par. s ladder / compact | ngspice bench s ladder / compact |
|---|---|---|---|---|---|---|---|
| DATA | 1044 / 438 | 0.0005 / 0.112 | 0.0001 / 0.0236 | 0.23 % | 2.31 mV (0.23 %) | 0.1 / 0.0 | 3.8 / 0.9 |
