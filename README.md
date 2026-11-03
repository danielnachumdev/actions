# actions

**Shared GitHub Actions + release standards** for [danielnachumdev](https://github.com/danielnachumdev) repositories.

This repo is both:

1. **Reference** — playbook, templates, and examples for CI/CD and repo hygiene  
2. **Consumable** — versioned reusable workflows you call with `uses: danielnachumdev/actions/...@v1`

Product repos stay thin: they own domain tests and packaging; this repo owns label-driven semver, shared Python-uv CI, and the scripts behind them.

## Consume

Pin a **tag** (not `main`):

```yaml
jobs:
  test:
    uses: danielnachumdev/actions/.github/workflows/reusable-python-uv-ci.yml@v1
    with:
      python-versions: '["3.11","3.12","3.13"]'
      sync-args: "--group dev"
```

| Workflow | Purpose |
| -------- | ------- |
| `reusable-python-uv-ci.yml` | `uv sync` + pytest matrix |
| `reusable-release-label.yml` | PR must have exactly one of `bumpMajor` / `bumpMinor` / `bumpPatch` / `noBump` |
| `reusable-semver-github-release.yml` | After CI on `main`: bump → wheel → GitHub Release |

Copy-paste starters: [`templates/workflows/`](templates/workflows/) · [`templates/github/`](templates/github/)  
End-to-end library example: [`examples/python-uv-library/`](examples/python-uv-library/)  
Full checklist: [`PLAYBOOK.md`](PLAYBOOK.md)

## Scripts

| Path | Role |
| ---- | ---- |
| `scripts/release/release_semver.py` | Label → next `vX.Y.Z` (or skip on `noBump`) |
| `scripts/release/build_python_uv_wheel.sh` | Stamp version + `uv build --wheel` |

## Develop this repo

See [`AGENTS.md`](AGENTS.md). Tests: `uv sync --group dev && uv run pytest -q`.

## Versioning

Breaking workflow/input changes → new major tag (`v2`). Callers should pin `@v1` or a full `v1.x.y` tag.
