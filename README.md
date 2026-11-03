# actions

**One place to standardize CI and releases** across [danielnachumdev](https://github.com/danielnachumdev) repositories — short pins, sensible defaults, label-driven semver.

[![CI](https://github.com/danielnachumdev/actions/actions/workflows/ci.yml/badge.svg)](https://github.com/danielnachumdev/actions/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/danielnachumdev/actions)

Stop copying the same pytest matrix and release YAML into every library. **Pin `@v1` once**, keep product repos thin, and ship GitHub Releases when a PR says `bumpPatch` — not when someone remembers to bump a version file.

## Why this repo?

- **Short, declarative workflow names** — `ci.yml`, `label.yml`, `release.yml` (as short as reusable workflows allow)
- **Defaults that fit uv libraries** — Python 3.11–3.13, `uv sync --group dev`, pytest — override only when you need to
- **Auto-detect** — finds `pyproject.toml` and runs the right lane
- **Label-driven semver** — `bumpMajor` / `bumpMinor` / `bumpPatch` / `noBump` → GitHub Release + wheel
- **Templates included** — CODEOWNERS, Dependabot, thin consumer CI/CD starters

## Sixty-second start

```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
```

```yaml
# .github/workflows/cd.yml  (label gate + release after CI on main)
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

Copy-paste starters live under [`templates/`](templates/). Full checklist: [`PLAYBOOK.md`](PLAYBOOK.md).

## Who it’s for

Public and private **Python / uv** libraries in the danielnachumdev namespace (e.g. [gp_wrapper](https://github.com/danielnachumdev/gp_wrapper)). Heavier org stacks (GCP, Terraform, raft boards) stay on their own hubs — this repo stays focused.

## Learn more

| Doc | Audience |
| --- | -------- |
| [`AGENTS.md`](AGENTS.md) | Implementers & coding agents — inputs, layout, pitfalls, how to change this repo |
| [`PLAYBOOK.md`](PLAYBOOK.md) | Rollout checklist for a new consumer |
| [`examples/python-uv-library/`](examples/python-uv-library/) | End-to-end library wiring |

## License

MIT — reuse freely; pin a tag in production.
