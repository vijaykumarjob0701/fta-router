import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import {
  DatasetError,
  loadExamples,
  loadJsonl,
  summarise,
  validateFile,
  writeJsonl,
} from "../src/index.ts";
import { validateRows } from "../src/dataset.ts";
import { INVALID_JSONL, VALID_JSONL, validRow } from "./helpers.ts";

test("load and summarise the valid fixture", () => {
  const examples = loadExamples(VALID_JSONL);
  assert.equal(examples.length, 8);
  const actions = new Set(examples.map((example) => example.primary_action));
  assert.deepEqual(actions, new Set(["answer_small", "rag", "tools", "escalate_large"]));
  const summary = summarise(VALID_JSONL);
  assert.equal(summary.n, 8);
  assert.equal(summary.primary_action.answer_small, 3);
  assert.equal(summary.primary_action.rag, 2);
  assert.equal(summary.primary_action.tools, 2);
  assert.equal(summary.primary_action.escalate_large, 1);
});

test("validateFile reports schema and duplicate ids", () => {
  const errors = validateFile(INVALID_JSONL);
  const joined = errors.join("\n");
  assert.match(joined, /needs_rag/);
  assert.match(joined, /duplicate id/);
  assert.match(joined, /primary_action/);
});

test("loadExamples raises on invalid file", () => {
  assert.throws(() => loadExamples(INVALID_JSONL), DatasetError);
});

test("writeJsonl then reload matches", () => {
  const rows = loadJsonl(VALID_JSONL);
  const out = path.join(mkdtempSync(path.join(os.tmpdir(), "fta-router-")), "copy.jsonl");
  writeJsonl(out, rows);
  assert.deepEqual(loadJsonl(out), rows);
});

test("validateRows reports duplicate ids", () => {
  const rows = [
    validRow({ id: "a", query: "What is TCP?" }),
    validRow({ id: "a", query: "What is UDP?" }),
  ];
  const errors = validateRows(rows);
  assert.ok(errors.some((error) => error.includes("duplicate")));
});
