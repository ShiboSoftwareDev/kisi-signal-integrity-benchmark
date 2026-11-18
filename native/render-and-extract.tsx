import React from "react";
import { Circuit } from "@tscircuit/core";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { RoutedPipelineSolver } from "./pipeline/src/pipeline";
import { RouteNetworkSolver } from "./pipeline/src/simulation";
import { createNativeSolver } from "./pipeline/src/adapters";
import { convertCircuitJsonToPcbSvg } from "circuit-to-svg";
import { Resvg } from "@resvg/resvg-js";

const levels = process.argv.slice(2).length
  ? process.argv.slice(2)
  : ["level1-single-ended", "level1-differential", "level2-two-channels"];
const sources = Object.fromEntries(
  await Promise.all(
    ["sn74lvc1g04.ibs", "sn65hvd72.ibs"].map(async (name) => [
      `models/${name}`,
      await readFile(new URL(`models/${name}`, import.meta.url), "utf8"),
    ]),
  ),
);
for (const level of levels) {
  const out = new URL(
    level + "/",
    process.env.BENCH_OUTPUT_DIR
      ? pathToFileURL(process.env.BENCH_OUTPUT_DIR.replace(/\/$/, "") + "/")
      : new URL("../build/native/results/", import.meta.url),
  ).pathname;
  await mkdir(out, { recursive: true });
  const { default: Board } = await import(
    `./pipeline/examples/${level}/${level}.tsx`
  );
  const started = performance.now();
  const core = new Circuit({
    platform: {
      partsEngineDisabled: true,
      platformFetch: async (url) =>
        new Response(sources[`models/${String(url).split("/").at(-1)}`] ?? ""),
    },
  });
  console.log("RENDER", level);
  core.add(<Board />);
  await core.renderUntilSettled();
  const circuit = core.getCircuitJson();
  await writeFile(`${out}/circuit.json`, JSON.stringify(circuit, null, 2));
  const diagnostics = circuit.filter((r) => r.type.endsWith("_error"));
  await writeFile(
    `${out}/render-diagnostics.json`,
    JSON.stringify(diagnostics, null, 2),
  );
  const svg = convertCircuitJsonToPcbSvg(circuit as any, {
    width: 1000,
    height: 440,
    layer: "top",
    shouldDrawErrors: false,
    shouldDrawRatsNest: false,
    showCourtyards: false,
    showSolderMask: false,
    showPcbNotes: false,
    includeVersion: false,
  });
  await writeFile(`${out}/board.svg`, svg);
  await writeFile(`${out}/board.png`, new Resvg(svg).render().asPng());
  const solver = new RoutedPipelineSolver(
    { circuitJson: circuit as any, ibisSources: sources },
    {
      runSolver: createNativeSolver({ timeoutMs: 180000 }),
      progress: console.log,
    },
  );
  try {
    while (
      !solver.solved &&
      solver.getCurrentStageName() !== "RouteTransientSolver"
    ) {
      const before = solver.getCurrentStageName();
      await solver.stepAsync();
      if (before !== solver.getCurrentStageName()) {
        console.log(level, before, "done");
        const stage = solver.getStageOutput(before);
        if (stage)
          await writeFile(`${out}/${before}.json`, JSON.stringify(stage));
      }
    }
    const plan = solver.stageOutput("RoutedAdmissionSolver").value[0];
    const board = solver.stageOutput("RouteSectionsSolver").value[0];
    const fields = solver.stageOutput("RouteFieldsSolver").value[0];
    const bindings = solver.stageOutput("RouteBindingsSolver").value[0];
    const common = new RouteNetworkSolver({
      blockId: plan.id,
      name: plan.name,
      geometry: board.geometry,
      extracted: fields,
      bindings,
      materials: fields.materials,
      options: {
        ...plan.bindings.options,
        riseSeconds: 100e-12,
        refinement: 2,
        stepSeconds: 5e-12,
      },
      warnings: plan.warnings,
      artifactPrefix: "common",
    });
    common.solve();
    const compiled = common.getOutput().value;
    await writeFile(`${out}/compiled-vendor-local.cir`, compiled.deck);
    let depth = 0;
    let control = false;
    const passive = [];
    for (const line of compiled.deck.split("\n")) {
      if (/^\.subckt/i.test(line)) depth++;
      if (/^\.control/i.test(line)) control = true;
      if (
        depth === 0 &&
        !control &&
        line !== compiled.deck.split("\n")[0] &&
        /^[RLCKGEFHV]/.test(line) &&
        !/^VDECLARED/.test(line)
      )
        passive.push(line);
      if (/^\.ends/i.test(line)) depth--;
    }
    const references = bindings.electricalLines
      .filter((line) => /^VDECLARED/.test(line))
      .map((line, i) => {
        const fields = line.split(/\s+/);
        return `VREF${i} ${fields[1]} ${fields[2]} DC 0`;
      });
    await writeFile(
      `${out}/our-channel.lib`,
      [
        "* Native routed linear channel, including all controlled coupling/loss elements; IBIS and packages excluded",
        ...passive,
        ...references,
      ].join("\n") + "\n",
    );
    await writeFile(
      `${out}/our-evidence.json`,
      JSON.stringify(compiled.evidence, null, 2),
    );
    await writeFile(
      `${out}/metadata.json`,
      JSON.stringify(
        {
          level,
          status: "extracted",
          render_errors: diagnostics.length,
          elapsed_s: (performance.now() - started) / 1000,
          source_commit: "374229d3dd3ca4581053423604b715dfb11ac86b",
          nodes: compiled.evidence.endpoint_nodes,
          mappings: bindings.mappings,
          node_map: bindings.nodeMap,
          electrical_lines: bindings.electricalLines,
          passive_elements: passive.length,
          materials: fields.materials,
        },
        null,
        2,
      ),
    );
    console.log(
      "EXTRACTED",
      level,
      JSON.stringify({
        elements: passive.length,
        seconds: (performance.now() - started) / 1000,
        nodes: compiled.evidence.endpoint_nodes,
      }),
    );
  } catch (error) {
    await writeFile(
      `${out}/failure.json`,
      JSON.stringify(
        {
          error: String(error),
          stage: solver.getCurrentStageName(),
          render_diagnostics: diagnostics,
        },
        null,
        2,
      ),
    );
    console.error("FAILED", level, error);
    throw error;
  }
}
