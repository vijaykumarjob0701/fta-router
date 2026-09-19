/** 4-way behavioural routing schema (version 1.0). */

export const SCHEMA_VERSION = "1.0";

export const PRIMARY_ACTIONS = ["answer_small", "rag", "tools", "escalate_large"] as const;
export type PrimaryAction = (typeof PRIMARY_ACTIONS)[number];

export const REASONING_LEVELS = ["low", "medium", "high"] as const;
export type ReasoningLevel = (typeof REASONING_LEVELS)[number];

export const DOMAINS = [
  "general_knowledge",
  "company_current",
  "tool_action",
  "multi_hop_planning",
  "ambiguous",
  "safety_mild",
  "open_domain_qa",
] as const;
export type Domain = (typeof DOMAINS)[number];

export const REQUIRED_FIELDS = [
  "id",
  "query",
  "primary_action",
  "needs_rag",
  "needs_tools",
  "reasoning_level",
  "rationale",
  "domain",
] as const;

export type RoutingRecord = {
  id: string;
  query: string;
  primary_action: string;
  needs_rag: boolean;
  needs_tools: boolean;
  reasoning_level: string;
  rationale: string;
  domain: string;
};

export class SchemaError extends Error {
  readonly errors: string[];

  constructor(errors: string[]) {
    const list = [...errors];
    super(list.length ? list.join("; ") : "invalid routing example");
    this.name = "SchemaError";
    this.errors = list;
  }
}

export function isPrimaryAction(value: unknown): value is PrimaryAction {
  return typeof value === "string" && (PRIMARY_ACTIONS as readonly string[]).includes(value);
}

export function parsePrimaryAction(value: string): PrimaryAction {
  if (!isPrimaryAction(value)) {
    throw new SchemaError([`primary_action '${value}' not in ${PRIMARY_ACTIONS}`]);
  }
  return value;
}

export class RoutingExample {
  readonly id: string;
  readonly query: string;
  readonly primary_action: string;
  readonly needs_rag: boolean;
  readonly needs_tools: boolean;
  readonly reasoning_level: string;
  readonly rationale: string;
  readonly domain: string;

  constructor(fields: RoutingRecord) {
    this.id = fields.id;
    this.query = fields.query;
    this.primary_action = fields.primary_action;
    this.needs_rag = fields.needs_rag;
    this.needs_tools = fields.needs_tools;
    this.reasoning_level = fields.reasoning_level;
    this.rationale = fields.rationale;
    this.domain = fields.domain;
  }

  toDict(): RoutingRecord {
    return {
      id: this.id,
      query: this.query,
      primary_action: this.primary_action,
      needs_rag: this.needs_rag,
      needs_tools: this.needs_tools,
      reasoning_level: this.reasoning_level,
      rationale: this.rationale,
      domain: this.domain,
    };
  }

  static fromDict(
    row: Record<string, unknown>,
    options: { validate?: boolean } = {},
  ): RoutingExample {
    const validate = options.validate ?? true;
    if (validate) {
      const errors = validateExample(row);
      if (errors.length) {
        throw new SchemaError(errors);
      }
    }
    return new RoutingExample({
      id: String(row.id),
      query: String(row.query),
      primary_action: String(row.primary_action),
      needs_rag: Boolean(row.needs_rag),
      needs_tools: Boolean(row.needs_tools),
      reasoning_level: String(row.reasoning_level),
      rationale: String(row.rationale),
      domain: String(row.domain),
    });
  }
}

export function validateExample(
  row: Record<string, unknown>,
  options: { lineNo?: number } = {},
): string[] {
  const prefix = options.lineNo != null ? `line ${options.lineNo}: ` : "";
  const errors: string[] = [];

  for (const field of REQUIRED_FIELDS) {
    if (!(field in row)) {
      errors.push(`${prefix}missing required field '${field}'`);
    }
  }
  if (errors.length) {
    return errors;
  }

  if (typeof row.id !== "string" || !row.id.trim()) {
    errors.push(`${prefix}id must be a non-empty string`);
  }
  if (typeof row.query !== "string" || !row.query.trim()) {
    errors.push(`${prefix}query must be a non-empty string`);
  }
  if (typeof row.rationale !== "string" || !row.rationale.trim()) {
    errors.push(`${prefix}rationale must be a non-empty string`);
  }

  const action = row.primary_action;
  if (!(PRIMARY_ACTIONS as readonly unknown[]).includes(action)) {
    errors.push(`${prefix}primary_action '${String(action)}' not in ${PRIMARY_ACTIONS}`);
  }

  if (typeof row.needs_rag !== "boolean") {
    errors.push(`${prefix}needs_rag must be bool, got ${typeName(row.needs_rag)}`);
  }
  if (typeof row.needs_tools !== "boolean") {
    errors.push(`${prefix}needs_tools must be bool, got ${typeName(row.needs_tools)}`);
  }

  const level = row.reasoning_level;
  if (!(REASONING_LEVELS as readonly unknown[]).includes(level)) {
    errors.push(`${prefix}reasoning_level '${String(level)}' not in ${REASONING_LEVELS}`);
  }

  const domain = row.domain;
  if (!(DOMAINS as readonly unknown[]).includes(domain)) {
    errors.push(`${prefix}domain '${String(domain)}' not in ${DOMAINS}`);
  }

  if (action === "rag" && row.needs_rag !== true) {
    errors.push(`${prefix}primary_action=rag requires needs_rag=true`);
  }
  if (action === "tools" && row.needs_tools !== true) {
    errors.push(`${prefix}primary_action=tools requires needs_tools=true`);
  }

  return errors;
}

function typeName(value: unknown): string {
  if (value === null) {
    return "null";
  }
  return typeof value === "object" ? value.constructor?.name || "object" : typeof value;
}
