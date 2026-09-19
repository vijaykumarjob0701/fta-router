# One repo, multiple language packages

This repository is a **polyglot monorepo**: one GitHub project distributes the
same behavioural-router library on more than one language registry.

```
fta-router/
├── pyproject.toml              Python package (PyPI: fta-router)
├── src/fta_router/             import fta_router
├── tests/                      pytest + shared JSONL fixtures
├── javascript/                 TypeScript package (npm: fta-router)
│   ├── package.json
│   └── src/
├── .github/workflows/
│   ├── tests.yml               Python CI (unchanged)
│   ├── publish.yml             PyPI on tags v*
│   ├── js-tests.yml            Node CI
│   └── js-publish.yml          npm on tags js-v*
└── docs/MULTI_LANGUAGE.md      this file
```

Python stays at the **repository root** so the existing PyPI Trusted Publisher
path (`publish.yml` + GitHub environment `pypi`) does not move. JavaScript lives
in `javascript/` with its own `package.json`, lockfile, and workflows.

## Chosen release scheme: independent tag prefixes

Releases do **not** share one semver tag.

| Language | Registry | Git tag            | Workflow                         | GitHub environment |
| -------- | -------- | ------------------ | -------------------------------- | ------------------ |
| Python   | PyPI     | `v0.1.0` (`v*`)    | `.github/workflows/publish.yml`  | `pypi`             |
| JavaScript | npm    | `js-v0.1.0` (`js-v*`) | `.github/workflows/js-publish.yml` | `npm`           |

GitHub’s `v*` filter matches tags that *start with* `v`. A JS tag `js-v0.1.0`
does **not** trigger the PyPI workflow. The two version numbers can move
independently after the first `0.1.0` pair.

We did **not** use a single shared `v*` tag with path filters. That scheme is
simpler when every language always ships together, but it couples releases and
makes a Python-only hotfix accidentally publish npm (or the reverse) unless
every workflow’s path filter is perfect. Prefixes keep the blast radius obvious.

## Registries and authentication

No long-lived publish tokens are stored in this repository.

### PyPI (already documented in the root README)

OIDC Trusted Publisher → workflow `publish.yml`, environment `pypi`.
See [PyPI trusted publishers](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

### npm (TypeScript package)

OIDC Trusted Publishing → workflow **filename** `js-publish.yml` (npm wants the
filename only, not the path), environment `npm`.

Requirements from [npm trusted publishers](https://docs.npmjs.com/trusted-publishers):

- npm CLI **11.5.1+** and Node **22.14+** on the publisher job
- GitHub-hosted runner
- Workflow permission `id-token: write`
- Package `repository.url` matching this GitHub repo

npm automatically attaches provenance when publishing via OIDC from a public
repo. The workflow does not pass `--provenance` and does not set `NODE_AUTH_TOKEN`.

#### One-time author setup (no secrets in git)

Trusted Publisher is configured on an **existing** npm package page. Bootstrap
the first `0.1.0` once, then switch to OIDC.

1. Create an [npmjs.com](https://www.npmjs.com/) account (2FA on).
2. Create a GitHub Environment named `npm` (optional approval reviewers).
3. **Bootstrap publish** (first version only), using a *granular* automation
   token that you create on npm and then **delete**:
   - Locally, from `javascript/`:
     ```bash
     npm login
     npm ci
     npm test
     npm run build
     npm publish --access public
     ```
     npm will prompt for the token / 2FA. Do not commit an `.npmrc` that
     contains a token.
   - Or paste that same granular token into a temporary GitHub Actions secret
     (for example `NPM_TOKEN`), run `workflow_dispatch` on `js-publish.yml`
     *only after adding a one-line `NODE_AUTH_TOKEN` fallback*, then **remove
     the secret and the fallback** immediately. Prefer the local bootstrap;
     this repo’s committed workflow is OIDC-only on purpose.
4. On npmjs.com → package `fta-router` → **Settings → Trusted publishing**:
   - Provider: GitHub Actions
   - Organization or user: `vijaykumarjob0701`
   - Repository: `fta-router`
   - Workflow filename: `js-publish.yml`
   - Environment name: `npm`
   - Allowed actions: include `npm publish` (not stage-only) so the tag
     workflow can release directly
5. Revoke the bootstrap token. Subsequent releases: bump `javascript/package.json`,
   commit, then `git tag js-v0.1.1 && git push origin js-v0.1.1`.

Until step 4 is done, pushing a `js-v*` tag will run tests/build and then fail
npm authentication. That is expected.

If the unscoped name `fta-router` is taken by the time you publish, rename the
package in `javascript/package.json` to `@vijaykumarjob0701/fta-router` and
update the Trusted Publisher on that scoped package instead.

## CI

- Python: `.github/workflows/tests.yml` — pytest + ruff + `python -m build` on
  3.10 and 3.12 (all PRs / `main`). Unchanged so existing PyPI CI stays green.
- JavaScript: `.github/workflows/js-tests.yml` — `npm ci`, `npm test`,
  `npm run build` on Node 20 and 22.

Neither workflow needs OpenAI or Anthropic keys.

## API parity

The JS package mirrors the Python **public** surface: schema, JSONL dataset I/O,
metrics, and the three deterministic baselines, plus a CLI
(`validate-dataset`, `summarise`, `baseline`). Method names are camelCase.

Phase-2 simulation (`fta_router.phase2`) and Hugging Face training
(`fta_router.training`) stay Python-only.

Shared fixtures live in `tests/fixtures/` and are used by both test suites.

## Adding a third language later

Keep the incumbent packages where they already publish from. Add a new
directory (`rust/`, `go/`, …), a new tag prefix (`rs-v*`, `go-v*`), a new
test workflow, and a new OIDC publish workflow + registry environment. Document
the prefix in this file so tags never collide.
