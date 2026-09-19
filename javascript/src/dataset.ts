/** Load and validate behavioural routing JSONL datasets. */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import { RoutingExample, SchemaError, validateExample, type RoutingRecord } from "./schema.ts";

export class DatasetError extends Error {
  readonly errors: string[];

  constructor(errors: string[]) {
    const list = [...errors];
    super(list.length ? list.join("; ") : "invalid dataset");
    this.name = "DatasetError";
    this.errors = list;
  }
}

export function iterJsonl(filePath: string): Array<[number, Record<string, unknown>]> {
  const rows: Array<[number, Record<string, unknown>]> = [];
  let text: string;
  try {
    text = readFileSync(filePath, "utf8");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    throw new DatasetError([`cannot read ${filePath}: ${message}`]);
  }
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const lineNo = i + 1;
    const line = lines[i].trim();
    if (!line) {
      continue;
    }
    let row: unknown;
    try {
      row = JSON.parse(line);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new DatasetError([`${filePath}:${lineNo}: invalid JSON: ${message}`]);
    }
    if (row === null || typeof row !== "object" || Array.isArray(row)) {
      throw new DatasetError([
        `${filePath}:${lineNo}: JSON object required, got ${Array.isArray(row) ? "array" : typeof row}`,
      ]);
    }
    rows.push([lineNo, row as Record<string, unknown>]);
  }
  return rows;
}

export function loadJsonl(filePath: string): Record<string, unknown>[] {
  return iterJsonl(filePath).map(([, row]) => row);
}

export function loadExamples(filePath: string, options: { validate?: boolean } = {}): RoutingExample[] {
  const validate = options.validate ?? true;
  if (validate) {
    const errors = validateFile(filePath);
    if (errors.length) {
      throw new DatasetError(errors);
    }
  }
  return loadJsonl(filePath).map((row) => RoutingExample.fromDict(row, { validate: false }));
}

export function writeJsonl(filePath: string, rows: Array<Record<string, unknown> | RoutingRecord>): void {
  mkdirSync(path.dirname(filePath), { recursive: true });
  const body = rows.map((row) => JSON.stringify(row)).join("\n") + (rows.length ? "\n" : "");
  writeFileSync(filePath, body, "utf8");
}

export function validateFile(filePath: string): string[] {
  const errors: string[] = [];
  const seenIds = new Set<string>();
  let text: string;
  try {
    text = readFileSync(filePath, "utf8");
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return [`cannot read ${filePath}: ${message}`];
  }
  const name = path.basename(filePath);
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const lineNo = i + 1;
    const line = lines[i].trim();
    if (!line) {
      continue;
    }
    let row: unknown;
    try {
      row = JSON.parse(line);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      errors.push(`${name}:${lineNo}: invalid JSON: ${message}`);
      continue;
    }
    if (row === null || typeof row !== "object" || Array.isArray(row)) {
      errors.push(`${name}:${lineNo}: JSON object required`);
      continue;
    }
    const record = row as Record<string, unknown>;
    errors.push(...validateExample(record, { lineNo }));
    const rid = record.id;
    if (typeof rid === "string" && rid) {
      if (seenIds.has(rid)) {
        errors.push(`${name}:${lineNo}: duplicate id '${rid}'`);
      }
      seenIds.add(rid);
    }
  }
  return errors;
}

export function validateRows(rows: Array<Record<string, unknown>>): string[] {
  const errors: string[] = [];
  const seenIds = new Set<string>();
  rows.forEach((row, index) => {
    const lineNo = index + 1;
    errors.push(...validateExample(row, { lineNo }));
    const rid = row.id;
    if (typeof rid === "string" && rid) {
      if (seenIds.has(rid)) {
        errors.push(`line ${lineNo}: duplicate id '${rid}'`);
      }
      seenIds.add(rid);
    }
  });
  return errors;
}

export function labelDistribution(
  rows: Array<Record<string, unknown>>,
  field = "primary_action",
): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const row of rows) {
    const key = String(row[field]);
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return counts;
}

export function summarise(filePath: string): {
  path: string;
  n: number;
  primary_action: Record<string, number>;
  domain: Record<string, number>;
  reasoning_level: Record<string, number>;
} {
  const rows = loadJsonl(filePath);
  return {
    path: filePath,
    n: rows.length,
    primary_action: labelDistribution(rows, "primary_action"),
    domain: labelDistribution(rows, "domain"),
    reasoning_level: labelDistribution(rows, "reasoning_level"),
  };
}

export const summarize = summarise;

export function examplesToDicts(examples: RoutingExample[]): RoutingRecord[] {
  return examples.map((example) => example.toDict());
}

export { SchemaError };
