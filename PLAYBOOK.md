# Playbook: standardize a repo (CI + semver CD + hygiene)

Apply this to [danielnachumdev](https://github.com/danielnachumdev) libraries. Prefer **consuming** this repo over vendoring YAML.

## Folders vs flat workflows

GitHub docs: reusable workflows live in `.github/workflows/` and **subdirectories are not supported**.  
Organize with **short flat names** (`ci.yml`, `label.yml`, `semver.yml`).  
Composite actions **may** use `.github/actions/<name>/`.

## Goals

1. CI on supported Python versions before merge  
2. CD publishes GitHub Release + wheel only after CI on `main`  
3. Label-driven semver (`bumpMajor` / `bumpMinor` / `bumpPatch` / `noBump`)  
4. CODEOWNERS, Dependabot, branch protection / rulesets  
5. Marketing `README.md` vs developer `AGENTS.md`

## Consumer wiring

1. Copy [`templates/workflows/ci.yml`](templates/workflows/ci.yml) and [`cd.yml`](templates/workflows/cd.yml).  
2. Copy [`templates/github/CODEOWNERS`](templates/github/CODEOWNERS) and [`dependabot.yml`](templates/github/dependabot.yml).  
3. Create labels: `bumpMajor`, `bumpMinor`, `bumpPatch`, `noBump`, `dependencies`.  
4. Protect `main`: require **`CI / CI`** and **`Label / Label`** (nested reusable names when caller jobs are named `CI` / `Label`).  
5. Enable vulnerability alerts + private vulnerability reporting.  
6. Pin `@v1`.

### `ci.yml` inputs (all optional)

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `working-directory` | `.` | App root |
| `pyproject-path` | `pyproject.toml` | Relative to working-directory; presence → Python lane |
| `python-versions` | `["3.11","3.12","3.13"]` | Matrix JSON |
| `sync-args` | `--group dev` | `uv sync` |
| `pytest-args` | `-q` | `uv run pytest` |
| `disable-python` | `false` | Force skip Python |
| `allow-empty` | `false` | Succeed if nothing detected |

### Short pins

```yaml
uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
uses: danielnachumdev/actions/.github/workflows/label.yml@v1
uses: danielnachumdev/actions/.github/workflows/semver.yml@v1
```

## Labels / settings / ruleset

See earlier playbook commands in git history or run from README examples — same `gh label create` / `gh api` vulnerability / ruleset flow as gp_wrapper. Required contexts after short rename: **`CI / CI`**, **`Label / Label`**.

## Semver

[`scripts/release/release_semver.py`](scripts/release/release_semver.py) + default wheel build [`build_python_uv_wheel.sh`](scripts/release/build_python_uv_wheel.sh).  
Custom artifact: pass `build-command` into `semver.yml` (`TAG` in env).

## Verify

```bash
uv sync --group dev && uv run pytest -q
python3 scripts/release/release_semver.py --latest-tag v1.2.3 --label bumpPatch
```
