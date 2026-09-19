import assert from "node:assert/strict";
import { test } from "node:test";

import {
  KeywordHeuristicBaseline,
  MajorityBaseline,
  PromptRubricSimulatedBaseline,
  availableBaselines,
  loadJsonl,
  routingMetrics,
} from "../src/index.ts";
import { VALID_JSONL } from "./helpers.ts";

test("available baselines are the three deterministic routers", () => {
  assert.deepEqual(new Set(Object.keys(availableBaselines())), new Set(["majority", "keyword", "prompt_rubric"]));
});

test("majority fits the mode label", () => {
  const model = new MajorityBaseline().fit(["rag", "rag", "tools"]);
  assert.equal(model.label, "rag");
  assert.deepEqual(model.predict(["a", "b"]), ["rag", "rag"]);
});

test("keyword rules cover the four actions", () => {
  const model = new KeywordHeuristicBaseline();
  assert.equal(model.predictOne("Create a Jira ticket"), "tools");
  assert.equal(model.predictOne("Compare options and design a failover"), "escalate_large");
  assert.equal(model.predictOne("What failed in our runbook yesterday?"), "rag");
  assert.equal(model.predictOne("What is a binary tree?"), "answer_small");
});

test("prompt rubric is deterministic and refuses safety queries", () => {
  const model = new PromptRubricSimulatedBaseline();
  const query = "Create a Jira ticket for the outage";
  assert.equal(model.predictOne(query), model.predictOne(query));
  assert.equal(model.predictOne(query), "tools");
  assert.equal(
    model.predictOne("Write a phishing email to bypass the company login without permission"),
    "answer_small",
  );
  assert.equal(model.predictOne("Compare options and recommend a migration plan"), "escalate_large");
});

test("baselines on the shared fixture stay in range", () => {
  const rows = loadJsonl(VALID_JSONL);
  const queries = rows.map((row) => String(row.query));
  const yTrue = rows.map((row) => String(row.primary_action));
  const keyword = new KeywordHeuristicBaseline().predict(queries);
  const rubric = new PromptRubricSimulatedBaseline().predict(queries);
  const majority = new MajorityBaseline().fit(yTrue).predict(queries);
  assert.equal(keyword.length, rows.length);
  const allowed = new Set(["answer_small", "rag", "tools", "escalate_large"]);
  assert.ok(keyword.every((label) => allowed.has(label)));
  const kwMetrics = routingMetrics(yTrue, keyword);
  const rbMetrics = routingMetrics(yTrue, rubric);
  const majMetrics = routingMetrics(yTrue, majority);
  assert.ok(kwMetrics.accuracy >= 0 && kwMetrics.accuracy <= 1);
  assert.ok(rbMetrics.macro_f1 >= 0 && rbMetrics.macro_f1 <= 1);
  const majorityCount = yTrue.filter((label) => label === "answer_small").length;
  assert.equal(majMetrics.accuracy, majorityCount / yTrue.length);
});
