# actions

**One place to standardize CI and releases** across [danielnachumdev](https://github.com/danielnachumdev) repositories — short pins, layout auto-detect, label-driven semver.

[![CI](https://github.com/danielnachumdev/actions/actions/workflows/check.yml/badge.svg)](https://github.com/danielnachumdev/actions/actions/workflows/check.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/danielnachumdev/actions)

Stop copying the same pytest matrix and release YAML into every library. **Pin `@latest`**, keep product repos thin, and let **Detect** turn on the right lanes from repo layout. Ship GitHub Releases when a PR says `bumpPatch` — not when someone remembers to bump a version file.

This repository **defines** the reusable workflows and **consumes** them the same way (thin `check.yml` / `cd.yml` → `./` building blocks). Dogfood CD opts into `retags: '["latest"]'`, so floating **`latest`** tracks each successful release.

## Why this repo?

- **Smart umbrella `ci.yml`** — Detect → Python / Node / GitHub YAML / Alembic rebase / Terraform validate (+ plan/apply when WIF passed) / raft (when `.raft/` + SSH unlock)
- **Override or disable** — `disable-*`, `working-directory`, matrices, `*-push`; call lane workflows directly when needed
- **Short workflow names** — `ci.yml`, `python.yml`, `node.yml`, `github-yaml.yml`, `rebase-guard.yml`, `terraform-validate.yml`, `terraform.yml`, `raft-deploy.yml`, `cloudrun-deploy.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`, `dependabot-auto-merge.yml`, `validate-skills.yml`
- **Shared CI + optional post-merge knobs** — no consumer `event_name` expressions
- **Overridable job timeouts** on every reusable job
- **One semver concept, two stages** — validate labels in CI; bump + Release in CD (opt-in)
- **Allowed labels** — `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor` (exactly one)
- **Opt-in floating tags** — `retags: '["latest"]'` on CD; prefer consumer pins **`@latest`**
- **Opt-in Dependabot merge** / **PyPI** / **Cloud Run** / **Agent Skills validate** (direct call; not auto-detected)
- **Templates included** — CODEOWNERS, Dependabot, thin consumer starters

## Sixty-second start

```yaml
# .github/workflows/ci.yml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    # with: only for overrides / WIF / raft unlocks — Detect does the rest
  semver:
    name: Semver
    if: github.event_name == 'pull_request'
    uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@latest
```

```yaml
# .github/workflows/cd.yml  (after CI succeeds on main)
jobs:
  semver:
    name: Semver
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@latest
    with:
      sha: ${{ github.event.workflow_run.head_sha }}
      retags: '["latest"]'   # opt-in; omit / "" / [] = no floating moves
```

Prefer **`@latest`** so consumers track the floating tag CD moves after each release. Pin an immutable release tag (`@v1.5.0`, …) when you need a frozen SHA.

## Docs

| Doc | What |
| --- | ---- |
| [`HOW-TO-USE.md`](HOW-TO-USE.md) | Adopt in a consumer repo (checklist + detection table) |
| [`AGENTS.md`](AGENTS.md) | Implementation details for maintainers / coding agents |
| [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) | Feature request + bug report forms (aligned with [`danielnachumdev/template`](https://github.com/danielnachumdev/template)) |
| [`templates/`](templates/) | Copy-paste CI/CD / retag / Cloud Run / raft / Terraform + CODEOWNERS / Dependabot starters |

## Who it’s for

Any public or private repo that can pin this hub — **Python / uv**, **Node**, Terraform, raft VPS, plus optional Semver publishers (e.g. [gp_wrapper](https://github.com/danielnachumdev/gp_wrapper)).

## License

MIT — prefer `@latest`, or pin an immutable release tag when you need a freeze.
