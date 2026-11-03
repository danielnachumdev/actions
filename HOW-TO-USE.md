# How to use

Adopt `danielnachumdev/actions` in a consumer repo (CI + semver CD + hygiene).

## Folders

GitHub: reusable workflows are **flat** under `.github/workflows/`. Names: `ci.yml`, `python.yml`, `node.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`.

This repo itself dogfoods them via thin `check.yml` (`name: CI`) + `cd.yml` calling `./…` — same shape as the templates below (templates use cross-repo `@v1` pins).

## Pins: `@v1` vs `@latest`

| Pin | Meaning |
| --- | ------- |
| **`@v1`** | Floating major — stays on the latest release of major 1 (stable contract). **Prefer this.** |
| **`@latest`** | Always the newest successful release SHA (any major). |

Both are force-moved by CD after each release (`semver-cd` → `retag.yml`).

## Semver (one feature, two stages)

| Stage | Workflow | Behavior |
| ----- | -------- | -------- |
| **CI** (PR) | `semver-ci.yml` | Fail unless exactly one of `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |
| **CD** (after CI on `main`) | `semver-cd.yml` | Read merged PR label → bump / skip → wheel → GitHub Release → floating tags (`latest` + `vMAJOR`) → optional PyPI |

## Wire-up

1. Copy [`templates/workflows/ci.yml`](templates/workflows/ci.yml) + [`cd.yml`](templates/workflows/cd.yml)  
2. Copy [`templates/github/`](templates/github/) CODEOWNERS + dependabot  
3. Create labels: `noBump`, `bumpPatch`, `bumpMinor`, `bumpMajor`, `dependencies`  
   - Dependabot’s `labels:` in `dependabot.yml` (template includes **`dependencies`** + **`noBump`** for pip / npm / github-actions) only apply if those labels **already exist** on the repo. Without `noBump`, Semver CI fails on Dependabot PRs.  
4. Protect `main` (soft): require **`CI / CI`** (+ **`Semver / Semver`** if using CD); CODEOWNERS `@you`; required review; admin bypass OK  
5. Enable Security settings (see below) — Dependabot opens PRs; you merge  
6. Pin `@v1`  
7. PyPI publishers only: `publish-pypi: true` + repo secret `PYPI_API_TOKEN`

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
# optional standalone floating-tag mover:
uses: danielnachumdev/actions/.github/workflows/retag.yml@v1
```

### Pre-merge vs post-merge CI (no consumer expressions)

Set event-specific inputs on the reusable `ci.yml` — do **not** write
`python-versions: ${{ github.event_name == 'push' && '…' || '…' }}` in the thin orchestrator.

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
    with:
      python-versions: '["3.11","3.12","3.13"]'   # shared baseline (both events)
      python-versions-push: '["3.11","3.13"]'      # optional lighter post-merge
      skip-node-push: true                           # optional: skip Node on push only
```

Empty `*-pr` / `*-push` strings inherit the shared baseline. Defaults keep the **full matrix on both** PR and push. `workflow_dispatch` uses the push knobs. Global `disable-python` / `disable-node` still kill a lane for every event; `skip-*-pr` / `skip-*-push` only skip that event.

### Security settings (step 5)

Enable when the API allows (public repos; free-tier **private** often cannot — Pro or public required for several of these, and for branch protection).

UI: **Settings → Security / Code security**.

CLI (idempotent; replace `OWNER/REPO`):

```bash
# Dependabot alerts
gh api --method PUT repos/OWNER/REPO/vulnerability-alerts \
  -H "Accept: application/vnd.github+json"

# Dependabot security updates
gh api --method PUT repos/OWNER/REPO/automated-security-fixes \
  -H "Accept: application/vnd.github+json"

# Private vulnerability reporting
gh api --method PUT repos/OWNER/REPO/private-vulnerability-reporting \
  -H "Accept: application/vnd.github+json"

# Secret scanning + push protection + Dependabot security updates (repo flag)
gh api --method PATCH repos/OWNER/REPO --input - <<'EOF'
{
  "security_and_analysis": {
    "secret_scanning": { "status": "enabled" },
    "secret_scanning_push_protection": { "status": "enabled" },
    "dependabot_security_updates": { "status": "enabled" }
  }
}
EOF
```

Verify: `gh api repos/OWNER/REPO --jq .security_and_analysis` and vulnerability-alerts HTTP **204**.

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
