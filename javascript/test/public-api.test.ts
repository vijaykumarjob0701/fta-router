import assert from "node:assert/strict";
import { test } from "node:test";

import * as ftaRouter from "../src/index.ts";

test("version and public exports", () => {
  assert.equal(ftaRouter.__version__, "0.1.0");
  for (const name of [
    "PRIMARY_ACTIONS",
    "RoutingExample",
    "loadExamples",
    "routingMetrics",
    "MajorityBaseline",
    "KeywordHeuristicBaseline",
    "PromptRubricSimulatedBaseline",
    "isPrimaryAction",
    "validateFile",
  ] as const) {
    assert.ok(name in ftaRouter, `missing export ${name}`);
  }
});
