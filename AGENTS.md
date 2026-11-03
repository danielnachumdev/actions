# AGENTS.md — danielnachumdev/actions

Implementation guide for maintainers and coding agents changing **this** repo.  
Pitch / consumer quickstart: [`README.md`](README.md). Adoption checklist: [`HOW-TO-USE.md`](HOW-TO-USE.md).

---

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + templates; **also a consumer** of those blocks |
| Toolchain | [uv](https://docs.astral.sh/uv/) + `pyproject.toml` / `uv.lock` (test harness only — not published) |
| Python | `>=3.11` (CI matrix **3.11, 3.12, 3.13** via reusable `ci.yml` defaults) |
| Tests | `tests/` — pytest; **never delete** |
| Workflows | **Flat** under `.github/workflows/` (no subdirs — GitHub rule) |
| Building blocks | `ci.yml`, `python.yml`, `node.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`, `dependabot-auto-merge.yml`, `raft-deploy.yml` (`workflow_call` only; optional PyPI job on CD) |
| Dogfood | Thin `check.yml` (`name: CI`) + `cd.yml` call `./.github/workflows/…` |
| Pinning (consumers) | Prefer **`@v1`**; **`@latest`** only if CD opts into `retags: '["latest"]'` |
| Semver labels | Exactly one of: `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |
| Secrets | Never commit API tokens, `.pypirc`, or credential files. Thin CD may map `PYPI_API_TOKEN` by name (needed for `publish-pypi: true`; empty OK when PyPI-off / OIDC is caller-inlined). |

```text
.
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── actions/detect-layout/   # composite used by reusable ci.yml detect
│   └── workflows/
│       ├── ci.yml               # reusable CI entry (workflow_call only)
│       ├── python.yml           # uv pytest matrix lane
│       ├── node.yml             # Node/TS lint+test matrix lane
│       ├── semver-ci.yml        # CI stage: validate bump label on PR
│       ├── semver-cd.yml        # CD: bump → wheel → Release → optional retag → optional PyPI
│       ├── retag.yml            # force-move explicit floating tags
│       ├── dependabot-auto-merge.yml
│       ├── raft-deploy.yml      # SSH + raft apply / doctor on a VPS
│       ├── check.yml            # dogfood thin CI (name: CI)
│       └── cd.yml               # dogfood thin CD
├── scripts/release/             # release_semver.py, build_python_uv_wheel.sh
├── templates/                   # consumer copy-paste CI/CD/retag/raft-deploy + CODEOWNERS / Dependabot (@v1)
├── examples/
├── tests/
├── pyproject.toml               # test harness (danielnachumdev-actions-tests); not on PyPI
├── README.md                    # Marketing / consumer pitch
├── HOW-TO-USE.md                # Consumer adoption checklist
└── AGENTS.md                    # This file
```

There is **one semver feature**. `semver-ci` and `semver-cd` are the same rules at different pipeline stages — not a separate “label” product.

Reusable `ci.yml` must **not** self-trigger on push/PR (that would collide with the thin orchestrator filename pattern and skip dogfooding). Triggers live only on thin `check.yml` / consumer `ci.yml`.

---

## Develop this repo

```bash
uv sync                 # runtime only → .venv (none today)
uv sync --group dev     # + pytest, pyyaml
# or: uv sync --all-groups
```

`tool.uv.default-groups` is empty — `uv sync` does **not** install `dev` by default.

| Task | Command |
| ---- | ------- |
| Tests | `uv run pytest -q` |
| Semver script smoke | `uv run python scripts/release/release_semver.py --latest-tag v1.2.3 --label bumpPatch` |

Config for pytest lives in `pyproject.toml`. Prefer editing floors / deps there and regenerating with `uv lock` / `uv sync --group dev`.

### Changing CI / workflows

1. Edit reusable blocks under `.github/workflows/` (`ci.yml`, `python.yml`, `node.yml`, `semver-*.yml`, `retag.yml`, `dependabot-auto-merge.yml`, `raft-deploy.yml`).
2. Keep dogfood thin `check.yml` / `cd.yml` aligned with [`templates/workflows/`](templates/workflows/) (relative `./` here; `@v1` in templates). Raft deploy is optional (template only; not dogfooded here).
3. Update [`HOW-TO-USE.md`](HOW-TO-USE.md) + templates when inputs, required check names, or adoption steps change.
4. Breaking inputs / check names → new **major** tag; update templates + consumers together.
5. Composite helpers under `.github/actions/` are for **this** repo’s reusable workflows; from `workflow_call`, relative `uses: ./.github/actions/...` resolves to the **caller** — prefer full `danielnachumdev/actions/...@v1` or inline (as `ci.yml` detect does).

---

## Consumer pins (contract reference)

```yaml
# CI — tests + semver label gate
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
    # with:
    #   python-versions: '["3.11","3.12","3.13"]'
    #   python-versions-push: '["3.11","3.13"]'   # lighter post-merge
    #   skip-node-push: true
  semver:
    name: Semver
    if: github.event_name == 'pull_request'
    uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
    with:
      standards-ref: v1
```

```yaml
# CD — after successful CI on main
permissions:
  contents: write
  # id-token: write  # only if you inline Trusted Publishing in this workflow
jobs:
  semver:
    name: Semver
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
    with:
      standards-ref: v1
      sha: ${{ github.event.workflow_run.head_sha }}
      # publish-pypi: true  # token path (requires PYPI_API_TOKEN)
      # Opt-in floating tags (empty/omit = no retag job):
      retags: '["latest"]'
    secrets:
      # User repos: map by name (inherit is org/enterprise only). Empty OK when PyPI-off.
      PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

Prefer required checks **`CI / CI`** and **`Semver / Semver`**.

Include PR types `labeled` / `unlabeled` on the consumer CI workflow so label edits re-run `semver-ci`.

### `ci.yml` inputs (optional)

Shared defaults (run on **both** `pull_request` and `push` / `workflow_dispatch`):

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `working-directory` | `.` | App root |
| `pyproject-path` | `pyproject.toml` | Presence → Python lane |
| `package-json-path` | `package.json` | Presence → Node lane |
| `python-versions` | `["3.11","3.12","3.13"]` | Matrix JSON (both events) |
| `node-versions` | `["20","22"]` | Matrix JSON (both events) |
| `sync-args` | `--group dev` | `uv sync` |
| `pytest-command` | `pytest -q` | Full invocation under `uv run` (cwd = working-directory; same PR + push) |
| `disable-python` / `disable-node` / `allow-empty` | `false` | Global lane kill / empty OK |
| `detect-timeout-minutes` | `5` | Detect job timeout |
| `python-timeout-minutes` | `30` | Passed to `python.yml` per matrix cell |
| `node-timeout-minutes` | `30` | Passed to `node.yml` per matrix cell |
| `ci-timeout-minutes` | `5` | CI gate job timeout |

Optional post-merge overrides (`push` / `workflow_dispatch` only). Omitted or `""` / `false` → shared default (empty does **not** clear a matrix; use `skip-*-push` to skip a lane). Do not pass `'[]'` as “run nothing”. Defaults preserve full matrices on both events.

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `python-versions-push` | `""` | Override Python matrix post-merge |
| `node-versions-push` | `""` | Override Node matrix post-merge |
| `sync-args-push` | `""` | Override `uv sync` args post-merge |
| `skip-python-push` | `false` | Skip Python post-merge only |
| `skip-node-push` | `false` | Skip Node post-merge only |

Consumers must **not** inject `github.event_name` expressions for matrices — use these inputs.

### `semver-cd.yml` inputs

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `sha` | required | Commit to tag / release |
| `standards-ref` | `v1` | Ref for scripts checkout |
| `dry-run` | `false` | Resolve only |
| `build-command` | (default wheel script) | Must print `wheel=<path>`; `TAG` in env |
| `python-version` / `latest-tag-override` | `3.13` / empty | Build Python / force latest tag |
| `publish-pypi` | `false` | Upload release wheel to PyPI via **API token** only |
| `retags` | `""` | JSON array of floating tags to force-move after release; `""` / `[]` = no-op |
| `timeout-minutes` | `30` | Semver job (bump / build / release) |
| `pypi-timeout-minutes` | `15` | Opt-in PyPI publish job |
| `retag-timeout-minutes` | `10` | Passed to `retag.yml` |


### `retag.yml` inputs (standalone or via `semver-cd`)

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `sha` | required | Commit floating tags should point at |
| `tags` | `["latest"]` | JSON array of tag names to force-move |
| `dry-run` | `false` | Print planned moves only |
| `timeout-minutes` | `10` | Retag job timeout |

Caller needs `permissions: contents: write`. Only moves tags listed in `tags`.

### `semver-cd.yml` secrets

| Secret | Required | Meaning |
| ------ | -------- | ------- |
| `PYPI_API_TOKEN` | no | Required when `publish-pypi: true`; unused when PyPI-off or Trusted Publishing is caller-inlined |

Callers **must**:
1. Pass `secrets: { PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }} }` — user repos cannot use `secrets: inherit` (org/enterprise only).
2. For **Trusted Publishing**, keep `publish-pypi: false` and inline a `pypi` job in thin `cd.yml` with `permissions.id-token: write` (see HOW-TO-USE). Do not expect OIDC to work from this reusable PyPI job ([warehouse#11096](https://github.com/pypi/warehouse/issues/11096)).

An unset token is fine (`required: false`) when PyPI-off / caller-inlined OIDC.

On a successful release, when `retags` is non-empty, `semver-cd` calls `retag.yml` with that list as `tags`. Empty `retags` (`""` or `[]`) skips the retag job. PyPI stays `needs: [semver]` only (parallel with retag). When `publish-pypi: true`, the **PyPI** job downloads that release’s `.whl` and runs `uv publish --token` (`PYPI_API_TOKEN` required). This repo’s dogfood `cd.yml` leaves PyPI **off** and opts into `retags: '["latest"]'`.

---

## Pitfalls

1. No `.github/workflows/**/subdirs` for reusable workflows.
2. `uses: ./.github/actions/...` inside `workflow_call` resolves to the **caller** — use full `danielnachumdev/actions/...@v1` or inline (as `ci.yml` detect does).
3. `uses:` must be a literal string.
4. No `${{ secrets.* }}` inside `workflow_call` `description:` fields.
5. On **this** repo, thin CI cannot be named `ci.yml` (that file is the reusable block) — use `check.yml` with `name: CI`.

---

## PRs, CI, and releases

1. Branch off `main`; open a PR into `main`.
2. Attach **exactly one** semver label: `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor`.
3. **CI** — dogfood `check.yml` → reusable `ci.yml` + `semver-ci.yml`. Prefer required checks **`CI / CI`** and **`Semver / Semver`**.
4. **CD** — dogfood `cd.yml` → `semver-cd.yml` after CI succeeds on `main`: bump → wheel → GitHub Release → optional `retags` → optional PyPI, or skip on `noBump`.
5. Version **source of truth** is GitHub Release tags (floating `vMAJOR` / optional `latest` when retags are enabled).
6. Dependabot PRs stay on `noBump`.
7. Docs-only / non-release changes use `noBump`.

### Repo gates (already configured)

- `.github/CODEOWNERS` — `@danielnachumdev`
- Prefer required **`CI / CI`** + **`Semver / Semver`**; code-owner reviews; no force-push to `main`
- Private vulnerability reporting via GitHub Security Advisories when enabled

---

## Sensitive / ignored

Do not commit: `.pypirc`, API tokens, credential JSON, `.venv/`, `venv/`, `dist/`, `__pycache__/`, `.actions-standards/`. Track `uv.lock`. Respect `.gitignore`.
