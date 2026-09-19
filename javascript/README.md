# fta-router (JavaScript / TypeScript)

TypeScript implementation of the FT-first 4-way behavioural router.

`answer_small` | `rag` | `tools` | `escalate_large`

This directory is the **npm** package. The Python package lives at the
repository root. Paper write-ups live in
[ft-behavioral-router](https://github.com/vijaykumarjob0701/ft-behavioral-router).

See [docs/MULTI_LANGUAGE.md](../docs/MULTI_LANGUAGE.md) for how one repo
publishes to both PyPI and npm.

## Install

```bash
npm install fta-router
```

From a clone:

```bash
cd javascript
npm ci
npm test
npm run build
```

Requires **Node 20+**. Zero runtime dependencies. No OpenAI / Anthropic keys.

## Quickstart

```ts
import {
  PRIMARY_ACTIONS,
  KeywordHeuristicBaseline,
  loadExamples,
  routingMetrics,
  validateFile,
} from "fta-router";

console.log(PRIMARY_ACTIONS);
// ['answer_small', 'rag', 'tools', 'escalate_large']

const errors = validateFile("tests/fixtures/routing_valid.jsonl");
if (errors.length) throw new Error(errors.join("\n"));

const examples = loadExamples("tests/fixtures/routing_valid.jsonl");
const queries = examples.map((ex) => ex.query);
const gold = examples.map((ex) => ex.primary_action);
const pred = new KeywordHeuristicBaseline().predict(queries);
console.log(routingMetrics(gold, pred).accuracy);
```

CLI (after `npm install -g fta-router` or `npx`):

```bash
npx fta-router validate-dataset path/to/train.jsonl --strict
npx fta-router baseline keyword --eval path/to/eval.jsonl
npx fta-router baseline majority --train path/to/train.jsonl --eval path/to/eval.jsonl
```

`prompt_rubric` is a **deterministic cue rubric**, not a live LLM call.

## Public API

JSONL field names match the Python schema (`primary_action`, `needs_rag`, …).
Function names are camelCase.

| Symbol | Role |
| --- | --- |
| `PRIMARY_ACTIONS`, `REASONING_LEVELS`, `DOMAINS` | Closed vocabularies |
| `RoutingExample`, `validateExample`, `isPrimaryAction`, `parsePrimaryAction` | Schema |
| `loadJsonl`, `loadExamples`, `validateFile`, `writeJsonl`, `summarise` | Dataset I/O |
| `routingMetrics`, `formatConfusion` | Accuracy, macro-F1, confusion |
| `MajorityBaseline`, `KeywordHeuristicBaseline`, `PromptRubricSimulatedBaseline` | Deterministic baselines |

Phase-2 simulation and Hugging Face training remain Python-only
(`fta_router.phase2`, `fta_router.training`).

## Publish

Tag prefix `js-v*` (example: `git tag js-v0.1.0`). OIDC Trusted Publishing —
no npm token in the repo. Setup steps: [docs/MULTI_LANGUAGE.md](../docs/MULTI_LANGUAGE.md).

## License

[MIT](LICENSE)
