import path from "node:path";
import { fileURLToPath } from "node:url";

export const FIXTURES_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../tests/fixtures",
);

export const VALID_JSONL = path.join(FIXTURES_DIR, "routing_valid.jsonl");
export const INVALID_JSONL = path.join(FIXTURES_DIR, "routing_invalid.jsonl");

export function validRow(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: "ex-1",
    query: "What is TCP?",
    primary_action: "answer_small",
    needs_rag: false,
    needs_tools: false,
    reasoning_level: "low",
    rationale: "Parametric networking fact.",
    domain: "general_knowledge",
    ...overrides,
  };
}
