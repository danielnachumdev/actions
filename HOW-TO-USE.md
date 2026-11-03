# How to use

Adopt `danielnachumdev/actions` in a consumer repo (CI + semver CD + hygiene).

## Folders

GitHub: reusable workflows are **flat** under `.github/workflows/`. Names: `ci.yml`, `python.yml`, `node.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`, `dependabot-auto-merge.yml`.

This repo itself dogfoods them via thin `check.yml` (`name: CI`) + `cd.yml` calling `./…` — same shape as the templates below (templates use cross-repo `@v1` pins).

## Pins: `@v1` vs `@latest`

| Pin | Meaning |
| --- | ------- |
| **`@v1`** | Stable major contract. **Prefer this.** |
| **`@latest`** | Newest successful release SHA when CD opts into `retags: '["latest"]'`. |

## Semver (one feature, two stages)

| Stage | Workflow | Behavior |
| ----- | -------- | -------- |
| **CI** (PR) | `semver-ci.yml` | Fail unless exactly one of `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |
| **CD** (after CI on `main`) | `semver-cd.yml` | Read merged PR label → bump / skip → wheel → GitHub Release → optional `retags` → optional PyPI |

## Wire-up

1. Copy [`templates/workflows/ci.yml`](templates/workflows/ci.yml) + [`cd.yml`](templates/workflows/cd.yml)  
2. Copy [`templates/github/`](templates/github/) CODEOWNERS + dependabot  
3. Create labels: `noBump`, `bumpPatch`, `bumpMinor`, `bumpMajor`, `dependencies`  
   - Dependabot’s `labels:` in `dependabot.yml` (template includes **`dependencies`** + **`noBump`** for pip / npm / github-actions) only apply if those labels **already exist** on the repo. Without `noBump`, Semver CI fails on Dependabot PRs.  
4. Protect `main` (soft): require **`CI / CI`** (+ **`Semver / Semver`** if using CD); CODEOWNERS `@you`; required review; admin bypass OK  
5. Enable Security settings (see below) — Dependabot opens PRs; optionally merge Dependabot PRs after CI (below)  
6. Pin `@v1`  
7. PyPI publishers only: `publish-pypi: true` + repo secret `PYPI_API_TOKEN`  
8. Floating tags: pass `retags: '["latest"]'` on thin CD (template does); omit / `""` / `[]` = no retag. Optional standalone: copy [`templates/workflows/retag.yml`](templates/workflows/retag.yml)

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
# optional standalone floating-tag mover:
uses: danielnachumdev/actions/.github/workflows/retag.yml@v1
# optional Dependabot merge after CI (from thin CI — see below):
uses: danielnachumdev/actions/.github/workflows/dependabot-auto-merge.yml@v1
```

### Opt-in floating retags (CD)

`semver-cd` does **not** move floating tags unless `retags` is a non-empty JSON
array. Pass the list you want force-moved to the release SHA (this repo and the
CD template opt into `latest`):

```yaml
# in thin cd.yml → semver-cd
with:
  sha: ${{ github.event.workflow_run.head_sha }}
  retags: '["latest"]'   # omit / "" / [] → skip retag job
```

### Optional standalone retag

Copy [`templates/workflows/retag.yml`](templates/workflows/retag.yml) for a
`workflow_dispatch` orchestrator that force-moves an explicit `tags` list to a
SHA (recoveries, custom aliases, dry-run):

```yaml
# .github/workflows/retag.yml  — see templates/workflows/retag.yml
jobs:
  retag:
    name: Retag
    uses: danielnachumdev/actions/.github/workflows/retag.yml@v1
    with:
      sha: ${{ inputs.sha }}      # required commit SHA
      tags: '["latest"]'          # tags to force-move
      dry-run: true               # print planned moves only
```

Caller needs `permissions: contents: write`. Inputs: `sha`, `tags`, `dry-run`.

### Shared CI + optional post-merge overrides (no consumer expressions)

Shared inputs (`python-versions`, `node-versions`, `sync-args`, `pytest-args`, …)
run on **both** `pull_request` and `push` / `workflow_dispatch`. Optional `*-push` /
`skip-*-push` override only post-merge when set — do **not** write
`python-versions: ${{ github.event_name == 'push' && '…' || '…' }}` in the thin orchestrator.

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
    with:
      python-versions: '["3.11","3.12","3.13"]'   # shared (both events)
      python-versions-push: '["3.11","3.13"]'      # optional lighter post-merge
      skip-node-push: true                           # optional: skip Node on push only
```

**Empty-string semantics:** omitting a `*-push` input and passing `""` are the same —
both **inherit the shared default**. An empty string does **not** clear the matrix or
mean “no versions”. To skip a lane on push only, set `skip-python-push` /
`skip-node-push`. Do not pass `'[]'` as a “run nothing” signal (it is a non-empty
override and will break the matrix). False `skip-*-push` also inherits (lane runs).
Defaults keep the **full matrix on both** PR and push. `workflow_dispatch` uses the
push knobs. Global `disable-python` / `disable-node` kill a lane for every event.

### Job timeouts (optional overrides)

Every reusable job has an explicit `timeout-minutes` (defaults match prior hardcodes).
Override via `workflow_call` inputs when a lane needs more (or less) time:

| Workflow | Inputs (defaults) |
| -------- | ----------------- |
| `ci.yml` | `detect-timeout-minutes` (5), `python-timeout-minutes` (30), `node-timeout-minutes` (30), `ci-timeout-minutes` (5) |
| `python.yml` / `node.yml` | `timeout-minutes` (30) |
| `semver-ci.yml` | `timeout-minutes` (5) |
| `semver-cd.yml` | `timeout-minutes` (30), `pypi-timeout-minutes` (15), `retag-timeout-minutes` (10) |
| `retag.yml` | `timeout-minutes` (10) |

```yaml
# example: longer Python matrix cells
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
    with:
      python-timeout-minutes: 45
```

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

### Dependabot merge after CI (optional opt-in)

Optional job on the thin CI orchestrator (commented example in [`templates/workflows/ci.yml`](templates/workflows/ci.yml)). It **merges** the Dependabot PR (squash + delete branch) once sibling jobs have already passed — it does not enable GitHub’s “Allow auto-merge” queue.

**Consumers must** set `needs:` to every PR job that must pass first so this job runs last:

```yaml
dependabot-auto-merge:
  name: Merge Dependabot PR
  needs: [ci, semver]
  if: github.event_name == 'pull_request' && github.event.pull_request.user.login == 'dependabot[bot]'
  permissions:
    contents: write
    pull-requests: write
  uses: danielnachumdev/actions/.github/workflows/dependabot-auto-merge.yml@v1
```

Also:

1. Job-level `contents: write` and `pull-requests: write` (shown above) so `GITHUB_TOKEN` can merge.
2. If classic branch protection has `require_code_owner_reviews: true` with review count `0`, set code-owner reviews to **false** so Dependabot can land after required CI checks (keep required status checks).
3. If branch protection requires checks that are **not** sibling jobs in this workflow, either add them to `needs:` or they can still block the merge.

Default remains **off** (job commented out in the template).

### Optional PyPI (same wheel as the GitHub Release)

1. Set repo secret **`PYPI_API_TOKEN`** (project-scoped or user upload token for that package).  
2. Thin `cd.yml`: `publish-pypi: true`, `permissions.id-token: write`, map `PYPI_API_TOKEN` **by name** (see template).  

**Notes (user-owned repos):**
- Map secrets by name — `secrets: inherit` is org/enterprise-only.
- Always set `id-token: write` on thin CD — `semver-cd` declares an OIDC-capable PyPI job (validated even when skipped). Token path is what we use today.

Default remains **GitHub Release only** (`publish-pypi: false`). CI auto-detects **Python** and/or **Node**.

### Python `__version__` (match CD bump)

Version **source of truth** is GitHub Release tags. CD bumps / stamps `pyproject.toml` `version` into the release checkout, then builds the wheel (and optionally publishes that same wheel to PyPI).

Expose the installed distribution version in package code — **do not hard-code** a string that drifts from CD:

```python
from importlib.metadata import version

# Use the exact [project].name from pyproject.toml (e.g. "gp_wrapper", "danielutils").
__version__ = version("your_package_name")
```

That way `import your_package; your_package.__version__` always reports the version stamped into the installed wheel. Re-export `__version__` from the package `__init__` if that matches your public API style.

The wheel build script still *can* rewrite a literal `__version__ = "…"` when present (legacy); prefer `importlib.metadata` so source never owns a manual bump.

## Verify

```bash
uv sync --group dev && uv run pytest -q
python3 scripts/release/release_semver.py --latest-tag v1.2.3 --label bumpPatch
```

See also: [`README.md`](README.md) (overview) · [`AGENTS.md`](AGENTS.md) (implementation details).
