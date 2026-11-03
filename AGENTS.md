# AGENTS.md — danielnachumdev/actions

Implementation and usage guide for **this** standards repo and its consumers.  
Product pitch: [`README.md`](README.md). Rollout checklist: [`PLAYBOOK.md`](PLAYBOOK.md).

---

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + consumer templates |
| Python | `>=3.11` test harness only (not a published package) |
| Pinning | Consumers use **`@v1`** (floating major) or `v1.x.y` |
| Workflows | **Flat** under `.github/workflows/` only — GitHub **forbids** subdirectories |
| Actions | Folders **allowed** under `.github/actions/<name>/` |

```text
.github/workflows/ci.yml       # public CI entry (+ dogfood on push/PR)
.github/workflows/python.yml   # uv pytest matrix lane
.github/workflows/label.yml    # release-label gate
.github/workflows/semver.yml  # bump → wheel → GitHub Release
.github/actions/detect-layout/ # optional composite (see pitfall below)
scripts/release/               # release_semver.py, build_python_uv_wheel.sh
templates/                     # copy-paste consumer starters
examples/                      # oriented walkthroughs
tests/                         # pytest for release_semver
PLAYBOOK.md
```

---

## How consumers call this (short pins)

Reusable workflows **cannot** use `uses: danielnachumdev/actions@v1` — that form is for root `action.yml` **Actions**. Workflows require:

```text
danielnachumdev/actions/.github/workflows/<file>.yml@v1
```

Keep `<file>` short: `ci`, `python`, `label`, `semver`.

### CI entry

```yaml
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@v1
    # with:  # all optional
    #   working-directory: .
    #   pyproject-path: pyproject.toml
    #   python-versions: '["3.11","3.12","3.13"]'
    #   sync-args: "--group dev"
    #   pytest-args: "-q"
    #   disable-python: false
    #   allow-empty: false
```

Prefer requiring branch-protection check **`CI / CI`** (caller job named `CI` + aggregate job named `CI`).

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `working-directory` | `.` | App root (monorepo package dir) |
| `pyproject-path` | `pyproject.toml` | Relative to working-directory; file present → Python lane |
| `python-versions` | `["3.11","3.12","3.13"]` | Matrix JSON |
| `sync-args` | `--group dev` | Passed to `uv sync` |
| `pytest-args` | `-q` | Passed to `uv run pytest` |
| `disable-python` | `false` | Force-skip Python lane |
| `allow-empty` | `false` | Succeed if no lane selected |

Direct Python lane (rare): `uses: …/python.yml@v1` with the same path/sync/pytest inputs.

### CD — label + release

Thin consumer `cd.yml` should keep `on: workflow_run` / `pull_request` / `workflow_dispatch` locally, then:

```yaml
jobs:
  label:
    name: Label
    if: github.event_name == 'pull_request'
    uses: danielnachumdev/actions/.github/workflows/label.yml@v1
    with:
      standards-ref: v1

  semver:
    name: Semver
    # if: successful CI on main / dispatch …
    uses: danielnachumdev/actions/.github/workflows/semver.yml@v1
    with:
      standards-ref: v1
      sha: ${{ github.event.workflow_run.head_sha }}  # or github.sha
      # dry-run, build-command, python-version, latest-tag-override — optional
```

Prefer required check **`Label / Label`**.

Release labels (exactly one per PR): `bumpMajor` | `bumpMinor` | `bumpPatch` | `noBump`.

Starters: [`templates/workflows/`](templates/workflows/) · [`templates/github/`](templates/github/).

---

## Scripts

| Path | Role |
| ---- | ---- |
| `scripts/release/release_semver.py` | Labels → next `vX.Y.Z` or skip (`noBump`) |
| `scripts/release/build_python_uv_wheel.sh` | Stamp version + `uv build --wheel` (default for `semver.yml`) |

Custom artifact: pass `build-command` into `semver.yml` (`TAG` is in the environment; command must print `wheel=<path>`).

---

## Critical pitfalls

1. **No workflow subdirectories** — cannot `uses: …/.github/workflows/python/ci.yml@v1`. Use flat short names.
2. **Relative composite actions in `workflow_call`** — `uses: ./.github/actions/…` resolves to the **caller** repo, not this one. `ci.yml` **inlines** detect for that reason. To call the composite explicitly: `uses: danielnachumdev/actions/.github/actions/detect-layout@v1`.
3. **`uses:` must be a literal** — no `${{ }}` in the `uses:` value.
4. **Do not put `${{ secrets.* }}` in `workflow_call` input/secret `description:` fields** — GitHub parses expressions there and the workflow can fail to load (0 jobs).

---

## Develop this repo

```bash
uv sync --group dev
uv run pytest -q
```

- Change shared CI/release behavior **here**, not by re-vendoring into consumers.
- Breaking inputs or required check names → new **major** tag (`v2`); update `templates/` + `PLAYBOOK.md` + consumer pins in the same effort.
- Dogfood: `ci.yml` also runs on push/PR to `main` of this repository.

### PR habit

Exactly one of `bumpMajor` | `bumpMinor` | `bumpPatch` | `noBump` on PRs into `main`.
