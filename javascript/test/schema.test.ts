import assert from "node:assert/strict";
import { test } from "node:test";

import {
  PRIMARY_ACTIONS,
  RoutingExample,
  SchemaError,
  isPrimaryAction,
  parsePrimaryAction,
  validateExample,
} from "../src/index.ts";
import { validRow } from "./helpers.ts";

test("primary actions are the four-way set", () => {
  assert.deepEqual([...PRIMARY_ACTIONS], ["answer_small", "rag", "tools", "escalate_large"]);
  assert.equal(isPrimaryAction("rag"), true);
  assert.equal(isPrimaryAction("teleport"), false);
});

test("parsePrimaryAction rejects unknown values", () => {
  assert.equal(parsePrimaryAction("tools"), "tools");
  assert.throws(() => parsePrimaryAction("browse"), SchemaError);
});

test("validateExample accepts a valid row", () => {
  assert.deepEqual(validateExample(validRow()), []);
});

test("rag requires needs_rag=true", () => {
  const errors = validateExample(validRow({ primary_action: "rag", needs_rag: false }));
  assert.ok(errors.some((error) => error.includes("needs_rag")));
});

test("tools requires needs_tools=true", () => {
  const errors = validateExample(validRow({ primary_action: "tools", needs_tools: false }));
  assert.ok(errors.some((error) => error.includes("needs_tools")));
});

test("fromDict raises on invalid domain", () => {
  assert.throws(() => RoutingExample.fromDict(validRow({ domain: "not-a-domain" })), (err: unknown) => {
    assert.ok(err instanceof SchemaError);
    assert.ok(err.errors.length > 0);
    return true;
  });
});

test("toDict / fromDict roundtrip", () => {
  const example = RoutingExample.fromDict(validRow());
  const again = RoutingExample.fromDict(example.toDict());
  assert.deepEqual(again.toDict(), example.toDict());
});
