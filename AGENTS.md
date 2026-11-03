# AGENTS.md — danielnachumdev/actions

Implementation guide for maintainers and coding agents.  
Pitch: [`README.md`](README.md). Consumer adoption checklist: [`HOW-TO-USE.md`](HOW-TO-USE.md).

---

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + templates; **also a consumer** of those blocks |
| Workflows | **Flat** under `.github/workflows/` (no subdirs — GitHub rule) |
| Building blocks | `ci.yml`, `python.yml`, `semver-ci.yml`, `semver-cd.yml` (`workflow_call` only; optional PyPI job) |
| Dogfood | Thin `check.yml` (`name: CI`) + `cd.yml` call `./.github/workflows/…` |
| Pinning (consumers) | **`@v1`** (floating major, moved by `semver-cd` on each release) |
| Semver labels | Exactly one of: `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |

```text
.github/workflows/ci.yml         # reusable CI entry (workflow_call only)
.github/workflows/python.yml     # uv pytest matrix lane
.github/workflows/semver-ci.yml  # CI stage: validate bump label on PR
.github/workflows/semver-cd.yml  # CD stage: bump → wheel → Release → vMAJOR → optional PyPI
.github/workflows/check.yml      # dogfood thin CI (name: CI)
.github/workflows/cd.yml         # dogfood thin CD
scripts/release/
templates/                       # consumer copy-paste (pins @v1)
examples/
tests/
```

There is **one semver feature**. `semver-ci` and `semver-cd` are the same rules at different pipeline stages — not a separate “label” product.

Reusable `ci.yml` must **not** self-trigger on push/PR (that would collide with the thin orchestrator filename pattern and skip dogfooding). Triggers live only on thin `check.yml` / consumer `ci.yml`.

---

## Consumer pins

```yaml
# CI — tests + semver label gate
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
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
  id-token: write  # required by semver-cd even if publish-pypi is false
jobs:
  semver:
    name: Semver
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
    with:
      standards-ref: v1
      sha: ${{ github.event.workflow_run.head_sha }}
      # publish-pypi: true
    secrets:
      # User repos: map by name (inherit is org/enterprise only). Empty OK for OIDC.
      PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

Prefer required checks **`CI / CI`** and **`Semver / Semver`**.

Include PR types `labeled` / `unlabeled` on the consumer CI workflow so label edits re-run `semver-ci`.

### `ci.yml` inputs (optional)

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `working-directory` | `.` | App root |
| `pyproject-path` | `pyproject.toml` | Presence → Python lane |
| `python-versions` | `["3.11","3.12","3.13"]` | Matrix JSON |
| `sync-args` | `--group dev` | `uv sync` |
| `pytest-args` | `-q` | `uv run pytest` |
| `disable-python` / `allow-empty` | `false` | Lane toggles |

### `semver-cd.yml` inputs

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `sha` | required | Commit to tag / release |
| `standards-ref` | `v1` | Ref for scripts checkout |
| `dry-run` | `false` | Resolve only |
| `build-command` | (default wheel script) | Must print `wheel=<path>`; `TAG` in env |
| `python-version` / `latest-tag-override` | `3.13` / empty | Build Python / force latest tag |
| `publish-pypi` | `false` | Upload release wheel to PyPI |

### `semver-cd.yml` secrets

| Secret | Required | Meaning |
| ------ | -------- | ------- |
| `PYPI_API_TOKEN` | no | Token fallback; omit when using Trusted Publishing only |

Callers **must**:
1. Pass `secrets: { PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }} }` — user repos cannot use `secrets: inherit` (org/enterprise only).
2. Grant `permissions.id-token: write` — `semver-cd`’s PyPI job requests OIDC, and GitHub validates that even when `publish-pypi` is false / the job is skipped.

An unset token is fine (`required: false`) for OIDC-only / PyPI-off.

On a successful release, `semver-cd` force-moves floating `vMAJOR` (e.g. `v1`) to the release SHA so `@v1` stays current. When `publish-pypi: true`, a follow-up **PyPI** job downloads that release’s `.whl` and runs `uv publish` (OIDC `always`, or `--token` if `PYPI_API_TOKEN` is set). This repo’s dogfood `cd.yml` leaves PyPI **off**.

---

## Pitfalls

1. No `.github/workflows/**/subdirs` for reusable workflows.
2. `uses: ./.github/actions/...` inside `workflow_call` resolves to the **caller** — use full `danielnachumdev/actions/...@v1` or inline (as `ci.yml` detect does).
3. `uses:` must be a literal string.
4. No `${{ secrets.* }}` inside `workflow_call` `description:` fields.
5. On **this** repo, thin CI cannot be named `ci.yml` (that file is the reusable block) — use `check.yml` with `name: CI`.

---

## Develop this repo

```bash
uv sync --group dev
uv run pytest -q
```

Breaking inputs/check names → new major tag; update templates + [`HOW-TO-USE.md`](HOW-TO-USE.md) + consumers together.

PRs into `main` need exactly one semver label: `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor`. Merge on `main` runs dogfood CD and creates the GitHub Release (unless `noBump`).
