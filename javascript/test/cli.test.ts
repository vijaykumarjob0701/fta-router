import assert from "node:assert/strict";
import { test } from "node:test";

import { main } from "../src/cli.ts";
import { INVALID_JSONL, VALID_JSONL } from "./helpers.ts";

function capture(fn: () => number): { code: number; stdout: string; stderr: string } {
  const originalOut = process.stdout.write.bind(process.stdout);
  const originalErr = process.stderr.write.bind(process.stderr);
  let stdout = "";
  let stderr = "";
  process.stdout.write = ((chunk: string | Uint8Array) => {
    stdout += String(chunk);
    return true;
  }) as typeof process.stdout.write;
  process.stderr.write = ((chunk: string | Uint8Array) => {
    stderr += String(chunk);
    return true;
  }) as typeof process.stderr.write;
  try {
    return { code: fn(), stdout, stderr };
  } finally {
    process.stdout.write = originalOut;
    process.stderr.write = originalErr;
  }
}

test("validate-dataset succeeds on the valid fixture", () => {
  const result = capture(() => main(["validate-dataset", VALID_JSONL]));
  assert.equal(result.code, 0);
  assert.match(result.stdout, /VALIDATION OK/);
});

test("validate-dataset fails on the invalid fixture", () => {
  const result = capture(() => main(["validate-dataset", INVALID_JSONL]));
  assert.equal(result.code, 1);
});

test("summarise and baseline print metrics", () => {
  const result = capture(() => {
    const a = main(["summarise", VALID_JSONL]);
    const b = main(["baseline", "keyword", "--eval", VALID_JSONL]);
    const c = main(["baseline", "majority", "--train", VALID_JSONL, "--eval", VALID_JSONL]);
    return a || b || c;
  });
  assert.equal(result.code, 0);
  assert.match(result.stdout, /primary_action/);
  assert.match(result.stdout, /accuracy/);
});

test("majority without --train fails", () => {
  const result = capture(() => main(["baseline", "majority", "--eval", VALID_JSONL]));
  assert.equal(result.code, 2);
});
