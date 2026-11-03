# AGENTS.md — danielnachumdev/actions

Implementation and usage guide. Pitch: [`README.md`](README.md). Rollout: [`PLAYBOOK.md`](PLAYBOOK.md).

---

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + templates |
| Workflows | **Flat** under `.github/workflows/` (no subdirs — GitHub rule) |
| Short names | `ci.yml`, `python.yml`, `semver-ci.yml`, `semver-cd.yml` |
| Pinning | **`@v1`** |
| Semver labels | Exactly one of: `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |

```text
.github/workflows/ci.yml         # public CI entry (+ dogfood)
.github/workflows/python.yml     # uv pytest matrix lane
.github/workflows/semver-ci.yml  # CI stage: validate bump label on PR
.github/workflows/semver-cd.yml  # CD stage: bump → wheel → GitHub Release
scripts/release/
templates/
examples/
tests/
```

There is **one semver feature**. `semver-ci` and `semver-cd` are the same rules at different pipeline stages — not a separate “label” product.

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
jobs:
  semver:
    name: Semver
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
    with:
      standards-ref: v1
      sha: ${{ github.event.workflow_run.head_sha }}
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

---

## Pitfalls

1. No `.github/workflows/**/subdirs` for reusable workflows.
2. `uses: ./.github/actions/...` inside `workflow_call` resolves to the **caller** — use full `danielnachumdev/actions/...@v1` or inline (as `ci.yml` detect does).
3. `uses:` must be a literal string.
4. No `${{ secrets.* }}` inside `workflow_call` `description:` fields.

---

## Develop this repo

```bash
uv sync --group dev
uv run pytest -q
```

Breaking inputs/check names → new major tag; update templates + playbook + consumers together.

PRs into `main` need exactly one semver label: `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor`.
