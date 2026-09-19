# fta-router

**FT-first hybrid behavioural router** — libraries for the 4-way action policy
used in Vijay Kumar’s routing research:

`answer_small` | `rag` | `tools` | `escalate_large`

This repository is a **polyglot monorepo**. It publishes the same conceptual
API to two registries:

| Language | Package | Registry | Import |
| --- | --- | --- | --- |
| Python 3.10+ | `fta-router` | [PyPI](https://pypi.org/project/fta-router/) | `fta_router` |
| TypeScript / Node 20+ | `fta-router` | [npm](https://www.npmjs.com/package/fta-router) | `fta-router` |

Experiment write-ups, datasets, and measured tables live in the paper companion:
[ft-behavioral-router](https://github.com/vijaykumarjob0701/ft-behavioral-router).

How one GitHub repo ships both packages (layout, tags, OIDC):
[docs/MULTI_LANGUAGE.md](docs/MULTI_LANGUAGE.md).

> This is a routing **research** package. Phase-2 modules (Python) simulate
> cost, local BM25, and fake tools. They are not a production assistant and
> they do not report a cloud bill.

## Repository layout

```
.
├── pyproject.toml                 Python package (stays at repo root)
├── src/fta_router/                import fta_router
├── tests/                         pytest + shared JSONL fixtures
├── javascript/                    TypeScript package (npm)
│   ├── package.json
│   └── src/
├── .github/workflows/
│   ├── tests.yml                  Python CI
│   ├── publish.yml                PyPI on v* tags
│   ├── js-tests.yml               Node CI
│   └── js-publish.yml             npm on js-v* tags
└── docs/MULTI_LANGUAGE.md
```

Python remains at the root so the existing PyPI Trusted Publisher path does not
move. JavaScript is a sibling package, not a rewrite of the Python tree.

## Install

### Python

Once published on PyPI:

```bash
pip install fta-router
```

From a clone of this repo (development):

```bash
pip install -e ".[dev]"
```

Optional extras:

| Extra | Packages | Use |
| --- | --- | --- |
| `dev` | pytest, ruff | tests and lint |
| `train` | torch, transformers, datasets, accelerate | local text-classifier fine-tune |

```bash
pip install "fta-router[train]"
pip install -e ".[dev,train]"
```

Requires **Python 3.10+**. Core install has **no** NumPy / PyTorch /
transformers dependency.

### JavaScript / TypeScript

Once published on npm:

```bash
npm install fta-router
```

From a clone:

```bash
cd javascript
npm ci
npm test
```

Requires **Node 20+**. Zero runtime dependencies. See
[javascript/README.md](javascript/README.md).

## Quickstart (Python)

```python
from fta_router import (
    PRIMARY_ACTIONS,
    KeywordHeuristicBaseline,
    load_examples,
    routing_metrics,
    validate_file,
)

print(PRIMARY_ACTIONS)
# ('answer_small', 'rag', 'tools', 'escalate_large')

errors = validate_file("tests/fixtures/routing_valid.jsonl")
assert errors == []

examples = load_examples("tests/fixtures/routing_valid.jsonl")
queries = [ex.query for ex in examples]
gold = [ex.primary_action for ex in examples]

pred = KeywordHeuristicBaseline().predict(queries)
print(routing_metrics(gold, pred)["accuracy"])
```

Validate a dataset from the CLI:

```bash
fta-router validate-dataset path/to/train.jsonl path/to/eval.jsonl --strict
fta-router baseline keyword --eval path/to/eval.jsonl
fta-router baseline majority --train path/to/train.jsonl --eval path/to/eval.jsonl
```

`prompt_rubric` is a **deterministic cue rubric**, not a live LLM call.

## Quickstart (TypeScript)

```ts
import {
  PRIMARY_ACTIONS,
  KeywordHeuristicBaseline,
  loadExamples,
  routingMetrics,
  validateFile,
} from "fta-router";

const examples = loadExamples("tests/fixtures/routing_valid.jsonl");
const pred = new KeywordHeuristicBaseline().predict(examples.map((ex) => ex.query));
console.log(routingMetrics(examples.map((ex) => ex.primary_action), pred).accuracy);
```

```bash
npx fta-router validate-dataset path/to/eval.jsonl --strict
npx fta-router baseline keyword --eval path/to/eval.jsonl
```

## Public API

JSONL records are schema version **1.0**. Required fields:

`id`, `query`, `primary_action`, `needs_rag`, `needs_tools`, `reasoning_level`, `rationale`, `domain`

Invariants: `primary_action=rag` requires `needs_rag=true`; `tools` requires `needs_tools=true`.

Imported from `fta_router` (Python) / `fta-router` (JS; camelCase names):

| Python | TypeScript | Role |
| --- | --- | --- |
| `PRIMARY_ACTIONS`, `REASONING_LEVELS`, `DOMAINS` | same | Closed vocabularies |
| `RoutingExample`, `validate_example`, `is_primary_action`, `parse_primary_action` | `validateExample`, `isPrimaryAction`, `parsePrimaryAction` | Schema |
| `load_jsonl`, `load_examples`, `validate_file`, `write_jsonl`, `summarise` | `loadJsonl`, `loadExamples`, `validateFile`, `writeJsonl`, `summarise` | Dataset I/O |
| `routing_metrics`, `format_confusion` | `routingMetrics`, `formatConfusion` | Accuracy, macro-F1, confusion |
| `MajorityBaseline`, `KeywordHeuristicBaseline`, `PromptRubricSimulatedBaseline` | same class names | Deterministic baselines |

## Optional modules (Python)

**Phase-2 simulation** (`fta_router.phase2`) — cost lookup under *illustrative*
unit rates, a local BM25 retriever, and Jira/GitHub tool stubs. Use for
stack-level what-ifs. Do not treat the numbers as production measurements.

```python
from fta_router.phase2 import CostModel, simulate_routes

model = CostModel()  # built-in illustrative rates
print(model.cost_for_route("escalate_large").cost)
```

**Training** (`fta_router.training`) — Hugging Face sequence classifier on
`primary_action`. Requires `pip install "fta-router[train]"`.

```bash
fta-router train --train data/train.jsonl --eval data/eval.jsonl --epochs 3
```

The CLI prints **measured** eval accuracy / macro-F1 from that run. This README
does not reprint paper scores.

These modules are **not** ported to JavaScript.

## Results

Do **not** treat this package README as a results table. For the research
numbers, splits, and discussion, see
[ft-behavioral-router](https://github.com/vijaykumarjob0701/ft-behavioral-router).

## Publishing from one repo

Independent **tag prefixes** so a Python release cannot collide with an npm
release:

| Package | Tag | Workflow | Registry | GitHub environment |
| --- | --- | --- | --- | --- |
| Python | `v0.1.0` (`v*`) | `publish.yml` | PyPI | `pypi` |
| JavaScript | `js-v0.1.0` (`js-v*`) | `js-publish.yml` | npm | `npm` |

Neither workflow stores a long-lived registry token. Both use **OIDC Trusted
Publishing**. First-time author setup (create the project, attach a Trusted
Publisher, bootstrap npm once) is documented in
[docs/MULTI_LANGUAGE.md](docs/MULTI_LANGUAGE.md) — do not invent or commit
secrets.

```bash
# Python → PyPI
git tag v0.1.0 && git push origin v0.1.0

# JavaScript → npm
git tag js-v0.1.0 && git push origin js-v0.1.0
```

### PyPI (summary)

1. Create a PyPI account (if needed) and verify email.
2. Create the project `fta-router` (or use a pending Trusted Publisher).
3. Add a **Trusted Publisher** for this GitHub repo:
   - Owner: `vijaykumarjob0701`
   - Repository: `fta-router`
   - Workflow: `publish.yml`
   - Environment: `pypi` (create a matching GitHub Environment named `pypi`)
4. Tag `v0.1.0`. The [publish workflow](.github/workflows/publish.yml) uploads
   via OIDC (`id-token: write`).

Until step 3 is done, pushing a `v*` tag will build artefacts but the publish
job will fail at PyPI authentication. That is expected.

Local check (does not upload):

```bash
python -m pip install build
python -m build
```

### npm (summary)

1. Create an npm account with 2FA.
2. Bootstrap `fta-router@0.1.0` **once** with a granular token
   (`cd javascript && npm publish --access public`), then revoke the token.
3. On the package page, add a **Trusted Publisher**:
   - Organization or user: `vijaykumarjob0701`
   - Repository: `fta-router`
   - Workflow filename: `js-publish.yml`
   - Environment: `npm`
4. Later releases: bump `javascript/package.json` and tag `js-v*`.
   [js-publish.yml](.github/workflows/js-publish.yml) publishes via OIDC.
   Requires npm CLI 11.5.1+ / Node 22.14+ on the publisher job.

If the unscoped name is taken, use `@vijaykumarjob0701/fta-router` and document
the rename in `javascript/package.json`.

## Development

Python:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
```

JavaScript:

```bash
cd javascript
npm ci
npm test
npm run typecheck
npm run build
```

CI runs Python checks on 3.10 / 3.12 and JavaScript checks on Node 20 / 22.
No LLM API keys are required.

## Author

Vijay Kumar — Dublin, Ireland — vijaykumarjob0701@gmail.com

## License

[MIT](LICENSE)
