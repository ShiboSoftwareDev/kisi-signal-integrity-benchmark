# Reproduction

## Recorded-data reanalysis

From the repo root, use Python 3.12 and the commands in the README. The four packages in `requirements.txt` are pinned to the experiment versions. `verify` needs only the standard library. Reanalysis and tests do not execute any upstream solver or fetch vendor models.

`python -m si_benchmark reanalyze` reads native channels under `data/cases/` and writes new results plus `eyes.png` under `build/reanalysis/`. To inspect the coarser pipeline extraction, add `--refinement 2 --output build/refinement2`. Source evidence is never overwritten.

Tests compare voltages, transfer functions, eye height/width, and step delay against the recorded run. They also check a resistor’s analytical DC divider, classify eyes using known PRBS labels, and ensure the physical-short block and native exporter exit 1 remain represented. Passing these tests means this recorded experiment reproduces; it does not mean all circuits or exports pass.

## Fresh native runs

These adapters reconstruct the original scientific protocol with portable paths. Required tools match the recorded environment: Python 3.12 with `requirements.txt`, Node, Bun, pnpm **11.25.0**, ngspice **47**, and KiCad CLI **10.0.6**. The bootstrap pins source and CLI hashes in [toolchain.lock.json](../provenance/toolchain.lock.json). Node’s CLI requires at least version 18; use a Node version compatible with pnpm 11.25.0 as well.

Obtain the original `sn74lvc1g04.ibs` and `sn65hvd72.ibs` files from Texas Instruments and put them in `.local/models/`. URLs, archive entries, and exact hashes are in [vendor-models.lock.json](../provenance/vendor-models.lock.json), under `cmos` and `rs485`; other entries in that unmodified upstream lockfile are unused here. No model text is bundled or synthesized.

```sh
python scripts/bootstrap_native.py
npx --yes pnpm@11.25.0 --dir .cache/upstream/pipeline install --frozen-lockfile
bun native/render-and-extract.tsx
bun native/refine_our.ts
python native/export_kicad.py
python native/run_drc.py
python native/run_our_ac.py
python native/run_our_ac.py --refinement4
python native/run_kisi.py
python native/validate_exports.py
bun native/run_native_ibis.ts
bun native/source_identity.ts
python -m si_benchmark reanalyze --data build/native/results --output build/native/analysis
```

Set `KICAD_CLI` to the executable’s absolute path if it is not on PATH; on macOS it is commonly inside the KiCad application bundle. Set `BENCH_OUTPUT_DIR` to an absolute directory to relocate native outputs. Native `build/` intermediates may contain vendor data and are ignored by Git. On macOS, KiCad DRC needs access to the normal desktop session; a restricted app sandbox can abort KiCad before it writes any report.

To reuse existing exact tools without downloading or reinstalling, bootstrap accepts `--pipeline /path/to/pipeline --kisi-source /path/to/kisi --kisi-cli /path/to/kisi.mjs --models /path/to/models`. It verifies source hashes, pinned Kisi commit, unmodified validator, release CLI hash, and model hashes before use. Existing directories or links pointing elsewhere are not overwritten. Do not run an install against shared reused dependencies.

For a complete native rerun, the strict exporter check is intentionally expected to return statuses **0 / 1 / 0** for DATA / BUS_P / D0. Its wrapper records those native statuses, checks them, and does not convert BUS_P into a passing result. D1 is not separately export-validated. KiCad’s DRC JSON retains all violations; the two-channel IBIS adapter blocks on verified shorts. The two-channel linear channels remain diagnostic data.

The validator’s differential ladder transient takes roughly 100 seconds in the recorded environment. `KISI_THREADS=1` and smooth roughness are set by the wrapper. Native profile checks, SPICE export validation, and the shared eye analysis measure different things; do not substitute one metric for another.

## Recorded evidence and curation

`data/cases/<name>/refinement4/` contains the final pipeline channel. The case root contains refinement 2 and independent Kisi exports in `kisi/` plus low-frequency anchors in `kisi-dc/`. Native exporter comparisons are in `native-export-validation/`. `.npz` channel and waveform arrays can be opened with NumPy using `allow_pickle=False`.

The immutable snapshot is indexed by [manifest.json](../provenance/manifest.json). [curation.json](../provenance/curation.json) records original and published hashes and which textual files had host paths sanitized. Numerical channel content is not rescaled or repaired. Vendor-containing stage outputs, vendor-containing compiled decks, duplicate AC decks, GUI lock files, and local view state were omitted. The adapters regenerate AC decks from the published passive libraries and port metadata.

The original figures and illustrated report are preserved. Reanalysis produces an additional plot rather than rewriting those historical artifacts. Native source reruns can vary with router/runtime/platform behavior; compare board identities before claiming bitwise reproduction. Only the single-ended recorded board matches the archived upstream accepted-board identity.
