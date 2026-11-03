# How to use

Adopt `danielnachumdev/actions` in a consumer repo (CI + semver CD + hygiene).

## Folders

GitHub: reusable workflows are **flat** under `.github/workflows/`. Names: `ci.yml`, `python.yml`, `node.yml`, `semver-ci.yml`, `semver-cd.yml`.

This repo itself dogfoods them via thin `check.yml` (`name: CI`) + `cd.yml` calling `./…` — same shape as the templates below (templates use cross-repo `@v1` pins).

## Semver (one feature, two stages)

| Stage | Workflow | Behavior |
| ----- | -------- | -------- |
| **CI** (PR) | `semver-ci.yml` | Fail unless exactly one of `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |
| **CD** (after CI on `main`) | `semver-cd.yml` | Read merged PR label → bump / skip → wheel → GitHub Release → move floating `vMAJOR` → optional PyPI |

## Wire-up

1. Copy [`templates/workflows/ci.yml`](templates/workflows/ci.yml) + [`cd.yml`](templates/workflows/cd.yml)  
2. Copy [`templates/github/`](templates/github/) CODEOWNERS + dependabot  
3. Create labels: `noBump`, `bumpPatch`, `bumpMinor`, `bumpMajor`, `dependencies`  
4. Protect `main` (soft): require **`CI / CI`** (+ **`Semver / Semver`** if using CD); CODEOWNERS `@you`; required review; admin bypass OK  
5. Enable Dependabot alerts + private vulnerability reporting (Dependabot opens PRs; you merge)  
6. Pin `@v1`  
7. PyPI publishers only: `publish-pypi: true` + repo secret `PYPI_API_TOKEN`

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
```

### Optional PyPI (same wheel as the GitHub Release)

1. Set repo secret **`PYPI_API_TOKEN`** (project-scoped or user upload token for that package).  
2. Thin `cd.yml`: `publish-pypi: true`, `permissions.id-token: write`, map `PYPI_API_TOKEN` **by name** (see template).  

**Notes (user-owned repos):**
- Map secrets by name — `secrets: inherit` is org/enterprise-only.
- Always set `id-token: write` on thin CD — `semver-cd` declares an OIDC-capable PyPI job (validated even when skipped). Token path is what we use today.

Default remains **GitHub Release only** (`publish-pypi: false`). CI auto-detects **Python** and/or **Node**.
## Verify

```bash
uv sync --group dev && uv run pytest -q
python3 scripts/release/release_semver.py --latest-tag v1.2.3 --label bumpPatch
```

See also: [`README.md`](README.md) (overview) · [`AGENTS.md`](AGENTS.md) (implementation details).
