# Example: Python uv library

1. Copy [`templates/workflows/ci.yml`](../../templates/workflows/ci.yml) and [`cd.yml`](../../templates/workflows/cd.yml)  
2. Copy [`templates/github/`](../../templates/github/) (CODEOWNERS + **dependabot.yml**)  
3. Create labels **before** Dependabot runs: `noBump`, `bumpPatch`, `bumpMinor`, `bumpMajor`, `dependencies`  
4. Required checks: **`CI / CI`**, **`Semver / Semver`**  
5. Pin `@v1` (stable major) — `@latest` floats on each CD release

Dependabot’s `labels:` (template: `dependencies` + `noBump` for **pip**, **npm**, and **github-actions**) only stick if those labels already exist. Without `noBump`, Semver CI fails on Dependabot PRs. Include the `npm` block only when the repo has a `package.json` (adjust `directory:` for monorepos, e.g. `/services/frontend`).

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@v1
```

Optional lighter post-merge matrix (no `event_name` expressions in the thin file):

```yaml
with:
  python-versions: '["3.11","3.12","3.13"]'
  python-versions-push: '["3.11","3.13"]'
```

Optional standalone retag (CD already moves `latest`): copy
[`templates/workflows/retag.yml`](../../templates/workflows/retag.yml).

Reference: [gp_wrapper](https://github.com/danielnachumdev/gp_wrapper).
