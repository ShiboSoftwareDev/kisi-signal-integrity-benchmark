import { pathToFileURL } from "node:url";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { RouteNetworkSolver } from "./pipeline/src/simulation";

for (const level of [
  "level1-single-ended",
  "level1-differential",
  "level2-two-channels",
]) {
  const folder = new URL(
    `${level}/`,
    process.env.BENCH_OUTPUT_DIR
      ? pathToFileURL(process.env.BENCH_OUTPUT_DIR.replace(/\/$/, "") + "/")
      : new URL("../build/native/results/", import.meta.url),
  );
  const val = async (name: string) =>
    JSON.parse(await readFile(new URL(name + ".json", folder), "utf8"))
      .value[0];
  const plan = await val("RoutedAdmissionSolver");
  const board = await val("RouteSectionsSolver");
  const fields = await val("RouteFieldsSolver");
  const bindings = await val("RouteBindingsSolver");
  const solver = new RouteNetworkSolver({
    blockId: plan.id,
    name: plan.name,
    geometry: board.geometry,
    extracted: fields,
    bindings,
    materials: fields.materials,
    options: {
      ...plan.bindings.options,
      riseSeconds: 100e-12,
      refinement: 4,
      stepSeconds: 5e-12,
    },
    warnings: plan.warnings,
    artifactPrefix: "refinement-control",
  });
  solver.solve();
  const compiled = solver.getOutput().value;
  const out = new URL("refinement4/", folder);
  await mkdir(out, { recursive: true });
  let depth = 0;
  let control = false;
  const lines = [];
  for (const [i, line] of compiled.deck.split("\n").entries()) {
    if (/^\.subckt/i.test(line)) depth++;
    if (/^\.control/i.test(line)) control = true;
    if (
      i &&
      depth === 0 &&
      !control &&
      /^[RLCKGEFHV]/.test(line) &&
      !/^VDECLARED/.test(line)
    )
      lines.push(line);
    if (/^\.ends/i.test(line)) depth--;
  }
  for (const [i, line] of bindings.electricalLines.entries())
    if (/^VDECLARED/.test(line)) {
      const fields = line.split(/\s+/);
      lines.push(`VREF${i} ${fields[1]} ${fields[2]} DC 0`);
    }
  await writeFile(
    new URL("our-channel.lib", out),
    [
      "* Same native extracted fields; refinement 4; all linear controlled elements retained",
      ...lines,
    ].join("\n") + "\n",
  );
  const metadata = JSON.parse(
    await readFile(new URL("metadata.json", folder), "utf8"),
  );
  metadata.refinement = 4;
  metadata.passive_elements = lines.length;
  await writeFile(
    new URL("metadata.json", out),
    JSON.stringify(metadata, null, 2),
  );
  console.log(level, lines.length, compiled.evidence.cells);
}
