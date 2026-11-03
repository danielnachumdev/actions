# actions

**One place to standardize CI and releases** across [danielnachumdev](https://github.com/danielnachumdev) repositories — short pins, sensible defaults, label-driven semver.

[![CI](https://github.com/danielnachumdev/actions/actions/workflows/ci.yml/badge.svg)](https://github.com/danielnachumdev/actions/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/danielnachumdev/actions)

Stop copying the same pytest matrix and release YAML into every library. **Pin `@v1` once**, keep product repos thin, and ship GitHub Releases when a PR says `bumpPatch` — not when someone remembers to bump a version file.

## Why this repo?

- **Short workflow names** — `ci.yml`, `semver-ci.yml`, `semver-cd.yml`
- **One semver concept, two stages** — validate labels in CI; bump + Release in CD
- **Allowed labels** — `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor` (exactly one)
- **Defaults that fit uv libraries** — Python 3.11–3.13, auto-detect `pyproject.toml`
- **Templates included** — CODEOWNERS, Dependabot, thin consumer starters

## Sixty-second start

```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
  semver:
    name: Semver
    if: github.event_name == 'pull_request'
    uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
```

```yaml
# .github/workflows/cd.yml  (after CI succeeds on main)
jobs:
  semver:
    name: Semver
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
    with:
      sha: ${{ github.event.workflow_run.head_sha }}
```

Starters: [`templates/`](templates/) · checklist: [`PLAYBOOK.md`](PLAYBOOK.md) · details: [`AGENTS.md`](AGENTS.md)

## Who it’s for

**Python / uv** libraries under danielnachumdev (e.g. [gp_wrapper](https://github.com/danielnachumdev/gp_wrapper)). Heavier org stacks stay on their own hubs.

## License

MIT — pin a tag in production.
