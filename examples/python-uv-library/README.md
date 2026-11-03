# Example: Python uv library (gp_wrapper-shaped)

Target: a public PyPI/GitHub library managed with **uv**, tested on **Python 3.11–3.13**, released via **label-driven semver** GitHub Releases.

## Wire-up checklist

1. Copy [`templates/workflows/ci.yml`](../../templates/workflows/ci.yml) → `.github/workflows/ci.yml`
2. Copy [`templates/workflows/cd.yml`](../../templates/workflows/cd.yml) → `.github/workflows/cd.yml`
3. Copy [`templates/github/CODEOWNERS`](../../templates/github/CODEOWNERS) → `.github/CODEOWNERS`
4. Copy [`templates/github/dependabot.yml`](../../templates/github/dependabot.yml) → `.github/dependabot.yml`
5. Create labels: `bumpMajor`, `bumpMinor`, `bumpPatch`, `noBump`, `dependencies`
6. Protect `main`: require checks **`CI`** and **`Release label`**; require code-owner reviews; disallow force-push
7. Ruleset (optional, raft-style): required status checks `CI` + `Release label` on `refs/heads/main`
8. Enable Dependabot alerts + private vulnerability reporting on the repo
9. Pin standards at a tag: replace `@v1` only after publishing tag `v1` on **this** repo

## Product-specific bits (stay in the library repo)

- `pyproject.toml` / `uv.lock` / package code
- Marketing [`README.md`](https://github.com/danielnachumdev/gp_wrapper/blob/main/README.md) vs developer [`AGENTS.md`](https://github.com/danielnachumdev/gp_wrapper/blob/main/AGENTS.md)
- Coverage thresholds, mypy/pylint config
- Custom `build-command` if the default `build_python_uv_wheel.sh` is not enough (e.g. SPA bake)

## Reference implementation

[danielnachumdev/gp_wrapper](https://github.com/danielnachumdev/gp_wrapper) — first consumer of this pattern (initially vendored; migrate to `uses: danielnachumdev/actions/...@v1` when ready).
