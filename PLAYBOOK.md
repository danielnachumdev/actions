# Playbook: standardize a repo (CI + semver CD + hygiene)

What we did for **gp_wrapper**, generalized so you can apply it to other [danielnachumdev](https://github.com/danielnachumdev) repos. Prefer **consuming** this repository’s reusable workflows over vendoring YAML.

---

## Goals

1. **CI** runs tests on supported Python versions before merge  
2. **CD** publishes a GitHub Release + artifact only after CI succeeds on `main`  
3. **Semver** is label-driven (`bumpMajor` / `bumpMinor` / `bumpPatch` / `noBump`) — no bot commits to bump versions on `main`  
4. **Hygiene**: CODEOWNERS, Dependabot, branch protection / rulesets, private vulnerability reporting  
5. **Docs split**: marketing `README.md` vs developer/agent `AGENTS.md`

---

## Decision: shared repo vs per-repo YAML

| Piece | Prefer |
| ----- | ------ |
| Pytest matrix (`uv`) | `uses: …/reusable-python-uv-ci.yml@v1` |
| Release label check | `uses: …/reusable-release-label.yml@v1` |
| Semver + Release + wheel | `uses: …/reusable-semver-github-release.yml@v1` |
| `workflow_run` / `pull_request` triggers | **Stay in product repo** (thin `ci.yml` / `cd.yml`) |
| SPA bake, e2e, path filters (raft-like) | **Stay in product repo**; pass custom `build-command` into semver workflow if needed |
| CODEOWNERS / dependabot.yml | Copy from `templates/github/` (GitHub does not compose these remotely) |
| Branch protection / rulesets | One-time `gh api` (script below); not stored as workflow code |

---

## Checklist (Python uv library)

### A. Product repo files

1. Add thin workflows from [`templates/workflows/`](templates/workflows/) (`ci.yml`, `cd.yml`), pin `@v1`.  
2. Add [`.github/CODEOWNERS`](templates/github/CODEOWNERS) and [`.github/dependabot.yml`](templates/github/dependabot.yml).  
3. Ensure `pyproject.toml` has `version = "X.Y.Z"` and `requires-python` matching the matrix.  
4. Rewrite docs: promotional `README.md`; `AGENTS.md` with setup / test / PR label / CD notes.  
5. Do **not** rely on committing version bumps for Releases — CD stamps versions in the ephemeral checkout only.

### B. GitHub labels

```bash
REPO=danielnachumdev/YOUR_REPO
gh label create bumpMajor -R "$REPO" --description "Breaking change — major semver bump on merge to main" --color B60205
gh label create bumpMinor -R "$REPO" --description "New feature — minor semver bump on merge to main" --color 0E8A16
gh label create bumpPatch -R "$REPO" --description "Bug fix / small change — patch semver bump on merge to main" --color 1D76DB
gh label create noBump -R "$REPO" --description "Docs/CI/chore — no GitHub Release on merge to main" --color C5DEF5
gh label create dependencies -R "$REPO" --description "Dependency / Dependabot updates" --color 0366d6
```

### C. Security / Dependabot settings

```bash
REPO=danielnachumdev/YOUR_REPO
gh api -X PUT "repos/${REPO}/vulnerability-alerts"
gh api -X PUT "repos/${REPO}/automated-security-fixes"
gh api -X PUT "repos/${REPO}/private-vulnerability-reporting"
```

### D. Ruleset + branch protection

Require checks **`CI`** (aggregate job name from the template) and **`Release label`**.

```bash
REPO=danielnachumdev/YOUR_REPO

gh api -X POST "repos/${REPO}/rulesets" -H "Accept: application/vnd.github+json" --input - <<'EOF'
{
  "name": "Release label required",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["refs/heads/main"], "exclude": [] } },
  "rules": [{
    "type": "required_status_checks",
    "parameters": {
      "strict_required_status_checks_policy": true,
      "do_not_enforce_on_create": false,
      "required_status_checks": [
        { "context": "Release label" },
        { "context": "CI" }
      ]
    }
  }],
  "bypass_actors": []
}
EOF

gh api -X PUT "repos/${REPO}/branches/main/protection" -H "Accept: application/vnd.github+json" --input - <<'EOF'
{
  "required_status_checks": { "strict": true, "contexts": ["CI", "Release label"] },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
EOF
```

### E. First release baseline

If the repo has **no** GitHub Releases yet, CD seeds `latest` from `pyproject.toml` `version`.  
First merge with `bumpPatch` on `0.9.12` → `v0.9.13`.  
Use `noBump` for pure CI/docs PRs.

### F. PR habit

Every PR into `main` gets **exactly one** of `bumpMajor` | `bumpMinor` | `bumpPatch` | `noBump`.  
Dependabot templates already request `noBump`.

---

## Semver rules (source of truth)

Implemented in [`scripts/release/release_semver.py`](scripts/release/release_semver.py):

- Labels are mutually exclusive; missing or multiple → fail closed  
- `noBump` → skip Release  
- Latest tag from GitHub Releases; else seed `v` + `pyproject` version  
- Tag format: `vMAJOR.MINOR.PATCH`

Wheel build default: [`scripts/release/build_python_uv_wheel.sh`](scripts/release/build_python_uv_wheel.sh) (stamps `pyproject.toml` / `__version__` / `publish.py` if present, then `uv build --wheel`).

---

## What stays product-specific

- Raft-style path filters, SPA bake, e2e, seed mirrors  
- Coverage % / mypy bounds / pylint  
- PyPI upload via `publish.py` / quickpub (optional; GitHub Release is the default ship path here)  
- Marketing README content  

For custom artifacts, call `reusable-semver-github-release.yml` with:

```yaml
with:
  build-command: bash scripts/release/build_release_wheel.sh "${TAG}" dist
```

(`TAG` is exported in the reusable job environment.)

---

## Migrating a vendored copy (e.g. gp_wrapper)

1. Replace local `.github/workflows/*.yml` with templates that `uses: danielnachumdev/actions/...@v1`  
2. Delete vendored `scripts/release/release_semver.py` if unused locally (keep a thin wrapper only if you override build)  
3. Keep product `AGENTS.md` pointing at this playbook for the shared parts  

---

## Verify locally

```bash
# in danielnachumdev/actions
uv sync --group dev
uv run pytest -q

python3 scripts/release/release_semver.py --latest-tag v1.2.3 --label bumpPatch
# → tag=v1.2.4
```
