import { pathToFileURL } from "node:url";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const levels = [
  "level1-single-ended",
  "level1-differential",
  "level2-two-channels",
];
const evidence = JSON.parse(
  await readFile(
    new URL(
      "pipeline/tests/evidence/signal-levels/rfc-boards.json",
      import.meta.url,
    ),
    "utf8",
  ),
);
const out = [];
for (const level of levels) {
  const c = JSON.parse(
    await readFile(
      new URL(
        `${level}/circuit.json`,
        process.env.BENCH_OUTPUT_DIR
          ? pathToFileURL(process.env.BENCH_OUTPUT_DIR.replace(/\/$/, "") + "/")
          : new URL("../build/native/results/", import.meta.url),
      ),
      "utf8",
    ),
  );
  const types = new Set([
    "pcb_board",
    "pcb_trace",
    "pcb_via",
    "pcb_copper_pour",
    "pcb_smtpad",
    "pcb_plated_hole",
    "pcb_stackup",
    "pcb_port",
    "source_component",
    "source_port",
    "source_net",
    "source_trace",
    "simulation_ibis_model",
  ]);
  const sorted = c
    .filter((r: any) => types.has(r.type))
    .map((r: any) => JSON.stringify(r))
    .sort();
  const hash = createHash("sha256")
    .update(JSON.stringify(sorted))
    .digest("hex");
  const historical = evidence.outputs.find((v: any) => v.level === level);
  out.push({
    level,
    rendered_hash: hash,
    historical_accepted_hash: historical.accepted_board_sha256,
    matches_historical_accepted_board:
      hash === historical.accepted_board_sha256,
    tsx_source_sha256: createHash("sha256")
      .update(
        await readFile(
          new URL(`pipeline/examples/${level}/${level}.tsx`, import.meta.url),
        ),
      )
      .digest("hex"),
  });
}
await writeFile(
  new URL("../build/native/board-source-identities.json", import.meta.url),
  JSON.stringify(
    {
      identity_method:
        "The exact boardIdentity() algorithm from the upstream render-example-images script.",
      examples: out,
      note: "Current TSX examples rerendered with their pinned published dependencies. Historical CSVs were not used as new solver output.",
    },
    null,
    2,
  ),
);
console.log(JSON.stringify(out));
