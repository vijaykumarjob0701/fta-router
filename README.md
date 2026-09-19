# fta-router

**FT-first hybrid behavioural router** — a small Python library for the 4-way
action policy used in Vijay Kumar’s routing research:

`answer_small` | `rag` | `tools` | `escalate_large`

This repository is the **installable package**. Experiment write-ups, datasets,
and measured tables live in the paper companion:
[ft-behavioral-router](https://github.com/vijaykumarjob0701/ft-behavioral-router).

Core install has **no** NumPy / PyTorch / transformers dependency. Training
helpers sit behind the optional `[train]` extra.

> This is a routing **research** package. Phase-2 modules simulate cost, local
> BM25, and fake tools. They are not a production assistant and they do not
> report a cloud bill.

## Install

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

Requires **Python 3.10+**.

## Quickstart

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

## Public API

Imported from `fta_router`:

| Symbol | Role |
| --- | --- |
| `PRIMARY_ACTIONS`, `REASONING_LEVELS`, `DOMAINS` | Closed vocabularies |
| `RoutingExample`, `validate_example`, `is_primary_action`, `parse_primary_action` | Schema |
| `load_jsonl`, `load_examples`, `validate_file`, `write_jsonl`, `summarise` | Dataset I/O |
| `routing_metrics`, `format_confusion` | Accuracy, macro-F1, confusion |
| `MajorityBaseline`, `KeywordHeuristicBaseline`, `PromptRubricSimulatedBaseline` | Deterministic baselines |

JSONL records are schema version **1.0**. Required fields:

`id`, `query`, `primary_action`, `needs_rag`, `needs_tools`, `reasoning_level`, `rationale`, `domain`

Invariants: `primary_action=rag` requires `needs_rag=true`; `tools` requires `needs_tools=true`.

## Optional modules

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

## Results

Do **not** treat this package README as a results table. For the research
numbers, splits, and discussion, see
[ft-behavioral-router](https://github.com/vijaykumarjob0701/ft-behavioral-router).

## Publishing to PyPI

The first upload is blocked on a one-time PyPI setup by the author. This repo
does **not** contain a PyPI token.

1. Create a PyPI account (if needed) and verify email.
2. Create the project `fta-router` (or let the first Trusted Publisher upload create it if you use pending publishers).
3. Add a **Trusted Publisher** for this GitHub repo:
   - Owner: `vijaykumarjob0701`
   - Repository: `fta-router`
   - Workflow: `publish.yml`
   - Environment: `pypi` (create a matching GitHub Environment named `pypi`)
4. Tag a release: `git tag v0.1.0 && git push origin v0.1.0`
5. The [publish workflow](.github/workflows/publish.yml) builds the sdist/wheel
   and uploads via OIDC (`id-token: write`). No long-lived API token is stored.

Until step 3 is done, pushing a `v*` tag will build artefacts but the publish
job will fail at PyPI authentication. That is expected.

Local check (does not upload):

```bash
python -m pip install build
python -m build
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
```

CI runs the same checks on pull requests (Python 3.10 and 3.12).

## Author

Vijay Kumar — Dublin, Ireland — vijaykumarjob0701@gmail.com

## License

[MIT](LICENSE)
