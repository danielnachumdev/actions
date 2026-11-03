# actions

**One place to standardize CI and releases** across [danielnachumdev](https://github.com/danielnachumdev) repositories — short pins, sensible defaults, label-driven semver.

[![CI](https://github.com/danielnachumdev/actions/actions/workflows/check.yml/badge.svg)](https://github.com/danielnachumdev/actions/actions/workflows/check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/danielnachumdev/actions)

Stop copying the same pytest matrix and release YAML into every library. **Pin `@v1` once**, keep product repos thin, and ship GitHub Releases when a PR says `bumpPatch` — not when someone remembers to bump a version file.

This repository **defines** the reusable workflows and **consumes** them the same way (thin `check.yml` / `cd.yml` → `./` building blocks).

## Why this repo?

- **Short workflow names** — `ci.yml`, `python.yml`, `node.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`
- **Auto lanes** — Python (`pyproject.toml`) and/or Node (`package.json`)
- **Shared CI + optional post-merge knobs** — shared defaults; optional `*-push` / `skip-*-push` (no consumer `event_name` expressions)
- **One semver concept, two stages** — validate labels in CI; bump + Release in CD
- **Allowed labels** — `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor` (exactly one)
- **Floating `@v1` and `@latest`** — CD retags both; prefer `@v1` for the stable major contract
- **Opt-in PyPI** — same release wheel via API token (OIDC later from thin CD)
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

## Docs

| Doc | What |
| --- | ---- |
| [`HOW-TO-USE.md`](HOW-TO-USE.md) | Adopt in a consumer repo (checklist) |
| [`AGENTS.md`](AGENTS.md) | Implementation details for maintainers / coding agents |
| [`templates/`](templates/) | Copy-paste CI/CD / retag + CODEOWNERS / Dependabot starters |

## Who it’s for

**Python / uv** libraries under danielnachumdev (e.g. [gp_wrapper](https://github.com/danielnachumdev/gp_wrapper)). Heavier org stacks stay on their own hubs.

## License

MIT — pin a tag in production.
