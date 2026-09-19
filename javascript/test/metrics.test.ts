import assert from "node:assert/strict";
import { test } from "node:test";

import { PRIMARY_ACTIONS, formatConfusion, routingMetrics } from "../src/index.ts";
import { accuracyScore, confusionMatrix, macroF1Score } from "../src/metrics.ts";

test("perfect predictions score 1.0", () => {
  const labels = [...PRIMARY_ACTIONS];
  const metrics = routingMetrics(labels, labels);
  assert.equal(metrics.accuracy, 1.0);
  assert.equal(metrics.macro_f1, 1.0);
  assert.deepEqual(metrics.labels, labels);
  assert.deepEqual(metrics.confusion_matrix, [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
  ]);
});

test("all-wrong-to-one-class accuracy and macro-F1", () => {
  const yTrue = ["answer_small", "rag", "tools", "escalate_large"];
  const yPred = ["answer_small", "answer_small", "answer_small", "answer_small"];
  const metrics = routingMetrics(yTrue, yPred);
  assert.equal(metrics.accuracy, 0.25);
  assert.ok(metrics.macro_f1 > 0.0 && metrics.macro_f1 < 0.5);
});

test("empty inputs are zero", () => {
  assert.equal(accuracyScore([], []), 0.0);
  assert.equal(macroF1Score([], [], ["a"]), 0.0);
  assert.deepEqual(confusionMatrix([], [], ["a"]), [[0]]);
});

test("formatConfusion includes labels and counts", () => {
  const text = formatConfusion(
    [
      [1, 0],
      [0, 2],
    ],
    ["yes", "no"],
  );
  assert.match(text, /yes/);
  assert.match(text, /no/);
  assert.match(text, /2/);
});
