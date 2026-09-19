#!/usr/bin/env node
/** Command-line interface for fta-router. */

import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { availableBaselines } from "./baselines.ts";
import { loadJsonl, summarise, validateFile } from "./dataset.ts";
import { formatConfusion, routingMetrics } from "./metrics.ts";

function printHelp(): void {
  console.log(`fta-router — FT-first hybrid behavioural router utilities.

Usage:
  fta-router validate-dataset <jsonl...> [--strict]
  fta-router summarise <jsonl>
  fta-router baseline <majority|keyword|prompt_rubric> --eval <jsonl> [--train <jsonl>]
`);
}

function cmdValidate(paths: string[], strict: boolean): number {
  const allErrors: string[] = [];
  for (const filePath of paths) {
    if (!existsSync(filePath)) {
      allErrors.push(`missing file: ${filePath}`);
      continue;
    }
    const errors = validateFile(filePath);
    allErrors.push(...errors);
    const summary = summarise(filePath);
    console.log(`== ${filePath}`);
    console.log(`   n=${summary.n}`);
    console.log(`   primary_action=${JSON.stringify(summary.primary_action)}`);
    console.log(`   domain=${JSON.stringify(summary.domain)}`);
    console.log(`   reasoning_level=${JSON.stringify(summary.reasoning_level)}`);
    if (strict && summary.n === 0) {
      allErrors.push(`${filePath}: empty file`);
    }
  }
  if (allErrors.length) {
    console.error("\nVALIDATION FAILED");
    for (const error of allErrors) {
      console.error(`  - ${error}`);
    }
    return 1;
  }
  console.log("\nVALIDATION OK");
  return 0;
}

function cmdSummarise(filePath: string): number {
  console.log(JSON.stringify(summarise(filePath), null, 2));
  return 0;
}

function takeFlag(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  if (index === -1) {
    return undefined;
  }
  return args[index + 1];
}

function cmdBaseline(name: string, args: string[]): number {
  const constructors = availableBaselines();
  const Ctor = constructors[name];
  if (!Ctor) {
    console.error(`unknown baseline '${name}'. choose: ${Object.keys(constructors).sort().join(", ")}`);
    return 2;
  }
  const evalPath = takeFlag(args, "--eval");
  const trainPath = takeFlag(args, "--train");
  if (!evalPath) {
    console.error("baseline requires --eval <jsonl>");
    return 2;
  }
  const model = new Ctor();
  const evalRows = loadJsonl(evalPath);
  if (name === "majority") {
    if (!trainPath) {
      console.error("majority baseline requires --train so the mode can be fit");
      return 2;
    }
    const trainRows = loadJsonl(trainPath);
    (model as { fit(labels: string[]): unknown }).fit(trainRows.map((row) => String(row.primary_action)));
  } else if ("fit" in model) {
    model.fit();
  }
  const preds = model.predict(evalRows.map((row) => String(row.query)));
  const yTrue = evalRows.map((row) => String(row.primary_action));
  const metrics = routingMetrics(yTrue, preds);
  const printable: Record<string, unknown> = {
    accuracy: metrics.accuracy,
    macro_f1: metrics.macro_f1,
    labels: metrics.labels,
    method: name,
    n_eval: evalRows.length,
  };
  if (name === "majority" && "label" in model) {
    printable.majority_label = (model as { label: string }).label;
  }
  if (name === "prompt_rubric") {
    printable.honesty = "Deterministic labeling-rubric simulation; NOT an LLM API prompted router.";
  }
  console.log(JSON.stringify(printable, null, 2));
  console.log(formatConfusion(metrics.confusion_matrix, metrics.labels));
  return 0;
}

export function main(argv: string[] = process.argv.slice(2)): number {
  if (!argv.length || argv[0] === "-h" || argv[0] === "--help") {
    printHelp();
    return argv.length ? 0 : 2;
  }
  const [command, ...rest] = argv;
  if (command === "validate-dataset") {
    const strict = rest.includes("--strict");
    const paths = rest.filter((arg) => arg !== "--strict");
    if (!paths.length) {
      console.error("validate-dataset requires at least one JSONL path");
      return 2;
    }
    return cmdValidate(paths, strict);
  }
  if (command === "summarise" || command === "summarize") {
    if (!rest[0]) {
      console.error("summarise requires a JSONL path");
      return 2;
    }
    return cmdSummarise(rest[0]);
  }
  if (command === "baseline") {
    const name = rest[0];
    if (!name) {
      console.error("baseline requires a name: majority | keyword | prompt_rubric");
      return 2;
    }
    return cmdBaseline(name, rest.slice(1));
  }
  console.error(`unknown command '${command}'`);
  printHelp();
  return 2;
}

function isDirectRun(): boolean {
  const entry = process.argv[1];
  if (!entry) {
    return false;
  }
  try {
    return path.resolve(fileURLToPath(import.meta.url)) === path.resolve(entry);
  } catch {
    return false;
  }
}

if (isDirectRun()) {
  process.exit(main());
}
