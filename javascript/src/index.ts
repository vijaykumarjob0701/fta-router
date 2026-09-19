/**
 * FTA behavioural router: FT-first 4-way action policy.
 *
 * Public surface mirrors the Python package conceptually. Phase-2 simulation
 * and Hugging Face training stay Python-only for now.
 */

export {
  KeywordHeuristicBaseline,
  MajorityBaseline,
  PromptRubricSimulatedBaseline,
  availableBaselines,
} from "./baselines.ts";
export {
  DatasetError,
  loadExamples,
  loadJsonl,
  summarise,
  summarize,
  validateFile,
  writeJsonl,
} from "./dataset.ts";
export { formatConfusion, routingMetrics } from "./metrics.ts";
export {
  DOMAINS,
  PRIMARY_ACTIONS,
  REASONING_LEVELS,
  SCHEMA_VERSION,
  RoutingExample,
  SchemaError,
  isPrimaryAction,
  parsePrimaryAction,
  validateExample,
} from "./schema.ts";

export const __version__ = "0.1.0";
