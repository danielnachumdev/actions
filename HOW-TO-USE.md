# How to use

Adopt `danielnachumdev/actions` in a consumer repo (CI + optional semver CD + hygiene).

## Folders

GitHub: reusable workflows are **flat** under `.github/workflows/`. Names: `ci.yml`, `python.yml`, `node.yml`, `github-yaml.yml`, `rebase-guard.yml`, `terraform-validate.yml`, `terraform.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`, `dependabot-auto-merge.yml`, `validate-skills.yml`, `cloudrun-deploy.yml`, `raft-deploy.yml`.

This repo itself dogfoods them via thin `check.yml` (`name: CI`) + `cd.yml` calling `./…` — same shape as the templates below (templates use cross-repo `@latest` pins).

## Auto-detect (umbrella `ci.yml`)

Thin consumers usually need **no `with:`**. Detect scopes markers to `working-directory` (default `.`). Repo-root `.github/` always drives the YAML parse lane.

| Marker | Lane | Credentials? |
| ------ | ---- | ------------ |
| `pyproject.toml` | `python.yml` | no |
| `package.json` | `node.yml` | no |
| `.github/` (repo root) | `github-yaml.yml` | no |
| `{alembic-root}/versions/` (default `alembic`) | `rebase-guard.yml` | no |
| `versions.tf` under `terraform/` (or `extra-terraform-module-paths`) | `terraform-validate.yml` always; `terraform.yml` plan/apply only if `workload_identity_provider` + `service_account` are non-empty | validate: no; apply: WIF |
| `.raft/` + app manifest | `raft-deploy.yml` when `raft-service`, `raft-git-repo`, and `secrets.VPS_SSH_KEY` are set | yes |

**Not auto-wired:** `cloudrun-deploy.yml`, `semver-*`, `dependabot-auto-merge.yml`, `validate-skills.yml` — call them from the thin orchestrator when you want them.

Inferred when inputs are left empty: `sync-args` from pyproject dependency groups; `node-versions` from `.nvmrc` / `engines.node` (else `["20","22"]`). Explicit values always win. Use `disable-*` / `allow-empty` / `*-push` to override.

## Pins: `@latest` vs immutable tags

| Pin | Meaning |
| --- | ------- |
| **`@latest`** | Newest successful release SHA. **Prefer this** — dogfood/template CD opts into `retags: '["latest"]'`. |
| **Immutable** (`@v1.5.0`, …) | Freeze on a specific release tag. |
| **`@v1`** | Floating major tag — **not** moved by default CD retags; only use if you maintain it yourself (e.g. standalone `retag.yml`). |

## Semver (optional — only if you publish versions)

**Add Semver only when the consumer creates versioned artifacts** (library/CLI wheels, GitHub Releases with tags, optional PyPI). Apps, sites, infra, assignments, and “just deploy `main`” repos should **omit** `semver-ci` / `semver-cd`, bump labels, and the **`Semver / Semver`** required check. CI + optional Dependabot merge (and your own deploy/raft CD) is enough.

| Stage | Workflow | Behavior |
| ----- | -------- | -------- |
| **CI** (PR) | `semver-ci.yml` | Fail unless exactly one of `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |
| **CD** (after CI on `main`) | `semver-cd.yml` | Read merged PR label → bump / skip → wheel → GitHub Release → optional `retags` → optional PyPI |

## Wire-up

1. Copy [`templates/workflows/ci.yml`](templates/workflows/ci.yml) (always). Copy [`cd.yml`](templates/workflows/cd.yml) **only if** you use Semver CD or want that thin publish shape.  
2. Copy [`templates/github/`](templates/github/) CODEOWNERS + dependabot  
3. Labels: always create `dependencies` (and any you use). Create `noBump` / `bumpPatch` / `bumpMinor` / `bumpMajor` **only if** adopting Semver.  
   - Dependabot’s `labels:` in `dependabot.yml` (template includes **`dependencies`** + **`noBump`**) only apply if those labels **already exist**. With Semver, without `noBump`, Semver CI fails on Dependabot PRs — drop the `noBump` label entry from `dependabot.yml` when Semver is not used.  
4. Protect `main` (soft): require **`CI / CI`** (+ **`Semver / Semver`** **only if** Semver is adopted); CODEOWNERS `@you`; required review; admin bypass OK  
5. Enable Security settings (see below) — Dependabot opens PRs; optionally merge Dependabot PRs after CI (below)  
6. Pin `@latest`  
7. PyPI publishers only (Semver CD): **token** → `publish-pypi: true` + `PYPI_API_TOKEN`; **Trusted Publishing** → inline a `pypi` job in thin `cd.yml` (not via the reusable job)   
8. Floating tags (Semver CD): pass `retags: '["latest"]'` on thin CD (template does); omit / `""` / `[]` = no retag. Optional standalone: copy [`templates/workflows/retag.yml`](templates/workflows/retag.yml)

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
# Semver — only if this repo publishes versions:
uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@latest
uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@latest
# optional standalone floating-tag mover:
uses: danielnachumdev/actions/.github/workflows/retag.yml@latest
# optional Dependabot merge after CI (from thin CI — see below):
uses: danielnachumdev/actions/.github/workflows/dependabot-auto-merge.yml@latest
# optional Agent Skills validation (repo-root */SKILL.md — see below):
uses: danielnachumdev/actions/.github/workflows/validate-skills.yml@latest
# optional raft VPS apply/redeploy (from thin CD — see below):
uses: danielnachumdev/actions/.github/workflows/raft-deploy.yml@latest
# optional Cloud Build / Cloud Run deploy (from thin CD — see below):
uses: danielnachumdev/actions/.github/workflows/cloudrun-deploy.yml@latest
# optional Terraform plan / apply (PR plan; post-merge apply — see below):
uses: danielnachumdev/actions/.github/workflows/terraform.yml@latest
```

### Agent Skills validation (optional)

Reusable job for repos that host [Agent Skills](https://agentskills.io) as repo-root `*/SKILL.md` directories (e.g. [danielnachumdev/skills](https://github.com/danielnachumdev/skills)). Runs pinned **skills-ref** after stripping known Cursor-only frontmatter keys (`disable-model-invocation`, `paths`, `icon`, `color`) into a temp copy so Cursor behavior stays in source while the open spec still gates CI.

Not auto-detected — add an explicit job on thin CI:

```yaml
jobs:
  validate-skills:
    name: Validate skills
    uses: danielnachumdev/actions/.github/workflows/validate-skills.yml@latest
    # with:
    #   working-directory: .
    #   timeout-minutes: 15
```

Prefer required check **`Validate skills / Validate skills`**. Locally: `./scripts/validate_skills.sh [SKILLS_ROOT]` from a checkout of this hub (or after copy). When Dependabot auto-merge is also enabled, include the job in `needs:` (e.g. `needs: [ci, validate-skills]`).

### Terraform (auto + optional direct)

Umbrella **`ci.yml`** already runs **`terraform-validate`** (fmt + `init -backend=false` + validate, no cloud creds) when `versions.tf` is found. Pass WIF on the umbrella to also run plan/apply:

```yaml
jobs:
  ci:
    name: CI
    permissions:
      contents: read
      id-token: write
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    with:
      workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}
      service_account: ${{ vars.GCP_WIF_SERVICE_ACCOUNT }}
      # skip-apply-push: true   # plan-only on push
```

Or call plan/apply alone via [`templates/workflows/terraform.yml`](templates/workflows/terraform.yml) / `terraform.yml@latest`. Validate alone: `terraform-validate.yml@latest`.

| Event (apply lane) | Default |
| ----- | ------- |
| `pull_request` | plan only |
| `push` | plan, then apply (unless `skip-apply-push: true`) |
| `workflow_dispatch` | plan, then apply |
| any + `apply: true` | force apply (including on PR) |

Caller needs `permissions.id-token: write` for apply. WIF pool trust on the **calling** repo (`attribute.repository`), not `job_workflow_ref` to this reusable file.

### Raft VPS apply / redeploy (optional)

Umbrella unlocks raft when **`.raft/`** exists and you pass `raft-service`, `raft-git-repo`, plus `secrets.VPS_SSH_KEY`. Or call [`raft-deploy.yml`](templates/workflows/raft-deploy.yml) directly from CD:

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    with:
      raft-service: my-app
      raft-git-repo: git@github.com:org/repo.git
    secrets:
      VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
```

```yaml
jobs:
  apply:
    name: Raft apply
    uses: danielnachumdev/actions/.github/workflows/raft-deploy.yml@latest
    with:
      service: my-app
      git-repo: git@github.com:org/repo.git
      ref: ${{ github.sha }}
      # host: 192.0.2.10          # optional; empty → vars.VPS_HOST
      # ssh-user: raft            # optional; empty → vars.VPS_USER → raft
    secrets:
      VPS_SSH_KEY: ${{ secrets.VPS_SSH_KEY }}
```

**Caller setup**

| Need | Where |
| ---- | ----- |
| Host | `with.host` **or** repo/org `vars.VPS_HOST` |
| SSH user | `with.ssh-user` **or** `vars.VPS_USER` (default `raft`) |
| SSH key | map `secrets.VPS_SSH_KEY` on the `secrets:` block (required) |

Missing host or SSH key fails with `::error::` (same as mealie). On the VPS the job ensures `raft` is on `PATH`, then:

```bash
raft auth test "${SERVICE}" --repo "${GIT_REPO}"
raft apply --git "${GIT_REPO}" --ref "${REF}"
raft doctor "${SERVICE}"   # skip with skip-doctor: true
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
    uses: danielnachumdev/actions/.github/workflows/retag.yml@latest
    with:
      sha: ${{ inputs.sha }}      # required commit SHA
      tags: '["latest"]'          # tags to force-move
      dry-run: true               # print planned moves only
```

Caller needs `permissions: contents: write`. Inputs: `sha`, `tags`, `dry-run`.

### Shared CI + optional post-merge overrides (no consumer expressions)

Shared inputs (`python-versions`, `node-versions`, `sync-args`, `pytest-command`, …)
run on **both** `pull_request` and `push` / `workflow_dispatch`.
Empty `sync-args` / `node-versions` → Detect infers. Optional `*-push` / `skip-*-push`
override only post-merge — do **not** write `event_name` expressions in the thin orchestrator.

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    with:
      python-versions: '["3.11","3.12","3.13"]'   # shared (both events)
      python-versions-push: '["3.11","3.13"]'      # optional lighter post-merge
      skip-node-push: true                           # optional: skip Node on push only
```

### Override the pytest command

Default Python lane runs `uv run pytest -q` in `working-directory` on **both** PR
and push. Pass `pytest-command` for the full invocation (suite path, markers, flags)
— there is no separate `pytest-args` input. For several suites, call `python.yml`
once per job:

```yaml
jobs:
  unit:
    name: Unit
    uses: danielnachumdev/actions/.github/workflows/python.yml@latest
    with:
      pytest-command: pytest tests/unit -q
  integration:
    name: Integration
    uses: danielnachumdev/actions/.github/workflows/python.yml@latest
    with:
      pytest-command: pytest tests/integration -q -m integration
```

Via `ci.yml` (single lane):

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    with:
      pytest-command: pytest tests/unit
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
| `ci.yml` | `detect` (5), `python`/`node` (30), `github-yaml`/`rebase-guard` (10), `terraform-validate` (15), `terraform` (30), `raft` (15), `ci` (5) |
| `python.yml` / `node.yml` | `timeout-minutes` (30) |
| `github-yaml.yml` / `rebase-guard.yml` | `timeout-minutes` (10) |
| `terraform-validate.yml` | `timeout-minutes` (15) |
| `semver-ci.yml` | `timeout-minutes` (5) |
| `semver-cd.yml` | `timeout-minutes` (30), `pypi-timeout-minutes` (15), `retag-timeout-minutes` (10) |
| `retag.yml` | `timeout-minutes` (10) |
| `cloudrun-deploy.yml` | `timeout-minutes` (45) |
| `raft-deploy.yml` | `timeout-minutes` (15); SSH `command_timeout` default `10m` |
| `terraform.yml` | `timeout-minutes` (30) |

```yaml
# example: longer Python matrix cells
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    with:
      python-timeout-minutes: 45
```

### Optional Cloud Run / Cloud Build deploy

Reusable job: WIF auth → `setup-gcloud` → `gcloud builds triggers run` for a SHA → stream logs. Path filters, GHCR, and raft SSH stay in the **caller**.

Copy [`templates/workflows/cloudrun-deploy.yml`](templates/workflows/cloudrun-deploy.yml) for a `workflow_dispatch` starter, or call from thin CD:

```yaml
# in thin cd.yml (after you resolve sha / path filters)
deploy-cloudrun:
  name: Deploy Cloud Run
  # needs: [changes]   # caller-owned gate
  permissions:
    contents: read
    id-token: write
  uses: danielnachumdev/actions/.github/workflows/cloudrun-deploy.yml@latest
  with:
    workload_identity_provider: projects/…/providers/github
    service_account: deploy-sa@PROJECT_ID.iam.gserviceaccount.com
    gcp_project: PROJECT_ID
    trigger: TRIGGER_ID_OR_NAME
    sha: ${{ needs.changes.outputs.sha }}
    # trigger_region: us-central1   # omit / "" = global
    # timeout-minutes: 45
```

Caller needs `permissions.id-token: write` (and `contents: read` as needed).

**WIF vs PyPI OIDC:** GCP Workload Identity pools usually trust `attribute.repository` (the **calling** consumer repo). Unlike PyPI Trusted Publishing, you typically do **not** bind on `job_workflow_ref` pointing at this reusable file — condition the pool on the consumer repo (and optional ref).

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

Optional job on the thin CI orchestrator (commented example in [`templates/workflows/ci.yml`](templates/workflows/ci.yml)). It **merges** the Dependabot PR (squash + delete branch) once sibling jobs have already passed — it does not enable GitHub’s “Allow auto-merge” queue (enable that in repo settings when you want the queue API / UI path as well).

**Gate so merge runs last.** The opt-in job **must** declare `needs:` listing every PR job that must succeed first. Without that edge, GitHub schedules it in parallel with CI; it can fail (or merge too early) while Unit/E2E/Semver are still running. `needs:` is what puts Dependabot merge last in the workflow graph.

**SHA guard before merge.** `needs:` only orders jobs inside *this* workflow run. If Dependabot force-pushes / rebases the PR while an older run’s merge job is still pending, `gh pr merge` would otherwise squash the *new* untested HEAD. The reusable workflow therefore compares the PR’s current `headRefOid` to `github.event.pull_request.head.sha` (the tip this run tested — **not** `github.sha`, which on `pull_request` is the ephemeral merge commit) and **skips merge (exit 0)** when they differ, so the newer CI run wins.

Thin CI **with Semver** (template / dogfood shape) — list every sibling PR job:

```yaml
dependabot-auto-merge:
  name: Merge Dependabot PR
  needs: [ci, semver]
  if: github.event_name == 'pull_request' && github.event.pull_request.user.login == 'dependabot[bot]'
  permissions:
    contents: write
    pull-requests: write
  uses: danielnachumdev/actions/.github/workflows/dependabot-auto-merge.yml@latest
```

Thin CI **without Semver**: `needs: [ci]` (or `[test]` / whatever your single required PR job id is) and the same `if:` / permissions / `uses:`.

Custom orchestrators (e.g. raft with Unit + E2E behind one aggregate success job): `needs:` that aggregate job instead of (or in addition to) leaf jobs — e.g. `needs: [ci]` when `ci` only succeeds after all required lanes pass. Same rule: merge must not start until every required PR check **in this workflow** has succeeded.

**Path-filtered / skipped siblings:** If the aggregate job uses `if: always()` so it can succeed while some lane jobs were **skipped**, GitHub still skips dependents of that aggregate unless the Dependabot job’s `if` also continues. Use:

```yaml
dependabot-auto-merge:
  name: Dependabot auto-merge
  needs: [ci]
  if: >-
    always() &&
    needs.ci.result == 'success' &&
    github.event_name == 'pull_request' &&
    github.event.pull_request.user.login == 'dependabot[bot]'
  permissions:
    contents: write
    pull-requests: write
  uses: danielnachumdev/actions/.github/workflows/dependabot-auto-merge.yml@latest
```

(Replace `ci` with your aggregate job id.) This belongs on the **caller**; the reusable workflow cannot undo skip-propagation by itself.

Also:

1. Job-level `contents: write` and `pull-requests: write` (shown above) so `GITHUB_TOKEN` can merge.
2. PRs that edit `.github/workflows/**` cannot be merged with `GITHUB_TOKEN` (no `workflows` scope). DAM **skips** those merges with a notice (job stays green); merge them manually.
3. If classic branch protection has `require_code_owner_reviews: true` with review count `0`, set code-owner reviews to **false** so Dependabot can land after required CI checks (keep required status checks).
4. If branch protection requires checks that are **not** sibling jobs in this workflow, either add them to `needs:` or they can still block the merge.
5. Do **not** require **`Semver / Semver`** on repos that omitted Semver.

Default remains **off** (job commented out in the template).

### Optional PyPI (same wheel as the GitHub Release)

Two supported paths — pick **one**:

| Path | Where | Setup |
| --- | --- | --- |
| **API token** | Reusable `semver-cd` PyPI job | `publish-pypi: true`, repo secret **`PYPI_API_TOKEN`** (account-scoped or project-scoped) |
| **Trusted Publishing** (OIDC) | **Caller-inlined** job in thin `cd.yml` only | `publish-pypi: false` on the reusable call; inline a `pypi` job that downloads the release wheel and runs `uv publish --trusted-publishing always`. Configure the PyPI Trusted Publisher for this repo’s **`cd.yml`**. |

**Why Trusted Publishing is not in the reusable job:** PyPI matches OIDC `job_workflow_ref`. Inside a `workflow_call`, that claim is the reusable workflow (`…/semver-cd.yml@…`), not the consumer’s `cd.yml`. PyPI does **not** support reusable workflows as Trusted Publishers ([troubleshooting](https://docs.pypi.org/trusted-publishers/troubleshooting/#reusable-workflows-on-github); [warehouse#11096](https://github.com/pypi/warehouse/issues/11096)).

**Trusted Publishing sketch** (inline in thin `cd.yml`):

```yaml
jobs:
  semver:
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@latest
    with:
      publish-pypi: false
      # …sha, standards-ref, etc.
    secrets:
      PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}  # unused when PyPI-off; still required by secrets: block
  pypi:
    name: PyPI
    needs: [semver]
    if: needs.semver.outputs.skip != 'true' && needs.semver.outputs.tag != ''
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: astral-sh/setup-uv@v10.3.3
        with:
          python-version: "3.13"
          ignore-empty-workdir: true
      - name: Download wheel from GitHub Release
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ needs.semver.outputs.tag }}
          REPO: ${{ github.repository }}
        run: |
          set -euo pipefail
          mkdir -p dist
          gh release download "${TAG}" --repo "${REPO}" --dir dist --pattern '*.whl'
      - name: Publish to PyPI (Trusted Publishing)
        run: |
          set -euo pipefail
          wheel="$(ls -1 dist/*.whl | head -1)"
          uv publish "${wheel}" --trusted-publishing always
```

**Notes (user-owned repos):**
- Map secrets by name — `secrets: inherit` is org/enterprise-only.
- Token path: map `PYPI_API_TOKEN`. OIDC path: grant `id-token: write` on thin CD for the **inline** job (not required for token-only).
- A project-scoped token cannot create a package that does not exist yet — use caller-inlined Trusted Publishing (or an account-scoped token) for first publish.

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
