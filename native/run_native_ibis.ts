import { pathToFileURL } from "node:url";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { RoutedPipelineSolver } from "./pipeline/src/pipeline";
import { createNativeSolver } from "./pipeline/src/adapters";

const root = new URL("./", import.meta.url);
const sources = Object.fromEntries(
  await Promise.all(
    ["sn74lvc1g04.ibs", "sn65hvd72.ibs"].map(async (n) => [
      `models/${n}`,
      await readFile(new URL(`models/${n}`, root), "utf8"),
    ]),
  ),
);
for (const level of [
  "level1-single-ended",
  "level1-differential",
  "level2-two-channels",
]) {
  const folder = new URL(
    `${level}/`,
    process.env.BENCH_OUTPUT_DIR
      ? pathToFileURL(process.env.BENCH_OUTPUT_DIR.replace(/\/$/, "") + "/")
      : new URL("../build/native/results/", root),
  );
  const drc = JSON.parse(
    await readFile(new URL("kicad-drc.json", folder), "utf8"),
  );
  const shorts = drc.violations.filter((v: any) => v.type === "shorting_items");
  if (shorts.length) {
    await writeFile(
      new URL("native-ibis-summary.json", folder),
      JSON.stringify(
        {
          status: "blocked_by_verified_short",
          shorts: shorts.length,
          reason:
            "Do not present a net-labelled simulation as a valid physical PCB result.",
        },
        null,
        2,
      ),
    );
    continue;
  }
  const circuit = JSON.parse(
    await readFile(new URL("circuit.json", folder), "utf8"),
  );
  const before = JSON.stringify(
    circuit.filter((r: any) => r.type.startsWith("pcb_")),
  );
  const block = circuit.find(
    (r: any) => r.type === "simulation_pcb_transient_channel_simulation",
  );
  block.duration_ms = (16 / block.bit_rate_bps) * 1000;
  const after = JSON.stringify(
    circuit.filter((r: any) => r.type.startsWith("pcb_")),
  );
  if (before !== after) throw new Error("Physical geometry changed");
  const start = performance.now();
  console.log("NATIVE", level);
  const solver = new RoutedPipelineSolver(
    { circuitJson: circuit, ibisSources: sources },
    {
      runSolver: createNativeSolver({ timeoutMs: 180000 }),
      progress: console.log,
    },
  );
  try {
    await solver.solveAsync();
    const capture = solver.getOutput().blocks[0].capture;
    await writeFile(
      new URL("native-ibis-capture.json", folder),
      JSON.stringify(capture),
    );
    const summary = {
      status: "completed",
      qualification: capture.qualification,
      bits: 16,
      bit_rate_bps: block.bit_rate_bps,
      duration_s: block.duration_ms / 1000,
      samples: capture.timestampsSeconds.length,
      seconds: (performance.now() - start) / 1000,
      pcb_records_unchanged: true,
      pcb_sha256: createHash("sha256").update(before).digest("hex"),
      probes: capture.probes.map((p) => ({
        name: p.name,
        min_v: Math.min(...p.voltageLevels),
        max_v: Math.max(...p.voltageLevels),
      })),
    };
    await writeFile(
      new URL("native-ibis-summary.json", folder),
      JSON.stringify(summary, null, 2),
    );
    console.log(JSON.stringify(summary));
  } catch (error) {
    await writeFile(
      new URL("native-ibis-summary.json", folder),
      JSON.stringify(
        {
          status: "failed",
          error: String(error),
          stage: solver.getCurrentStageName(),
        },
        null,
        2,
      ),
    );
    console.error(error);
    throw error;
  }
}
