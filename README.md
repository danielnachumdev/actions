# actions

**Shared GitHub Actions + release standards** for [danielnachumdev](https://github.com/danielnachumdev) repositories.

Reusable **workflows** must live flat under `.github/workflows/` (GitHub does **not** allow subfolders there). We use **short declarative filenames** instead. Composite **actions** may use folders under `.github/actions/`.

## Consume (short pins)

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
    # with:                    # all optional
    #   working-directory: .   # monorepo package dir
    #   pyproject-path: pyproject.toml
    #   python-versions: '["3.11","3.12","3.13"]'
    #   sync-args: "--group dev"
    #   pytest-args: "-q"
```

```yaml
jobs:
  label:
    name: Label
    uses: danielnachumdev/actions/.github/workflows/label.yml@v1
  release:
    name: Release
    uses: danielnachumdev/actions/.github/workflows/release.yml@v1
    with:
      sha: ${{ github.sha }}
```

| Workflow | Role |
| -------- | ---- |
| **`ci.yml`** | Entry: detect `pyproject.toml` → Python/`uv` pytest matrix → aggregate **`CI`** |
| **`python.yml`** | Python lane only (usually via `ci.yml`) |
| **`label.yml`** | PR must have exactly one of `bumpMajor` / `bumpMinor` / `bumpPatch` / `noBump` |
| **`release.yml`** | After CI on `main`: semver bump → wheel → GitHub Release |

Copy-paste starters: [`templates/workflows/`](templates/workflows/) · [`templates/github/`](templates/github/)  
Walkthrough: [`examples/python-uv-library/`](examples/python-uv-library/)  
Checklist: [`PLAYBOOK.md`](PLAYBOOK.md)

### Why not `uses: danielnachumdev/actions@v1`?

That short form is for **Actions** (`action.yml`). Multi-job CI/CD uses **reusable workflows**, which require `.github/workflows/<file>.yml@ref`. We keep `<file>` short (`ci`, `label`, `release`).

## Scripts

| Path | Role |
| ---- | ---- |
| `scripts/release/release_semver.py` | Label → next `vX.Y.Z` (or skip on `noBump`) |
| `scripts/release/build_python_uv_wheel.sh` | Stamp version + `uv build --wheel` |

## Develop

See [`AGENTS.md`](AGENTS.md). `uv sync --group dev && uv run pytest -q`.

## Versioning

Pin **`@v1`**. Breaking input/check-name changes → `v2`.
