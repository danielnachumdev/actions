# AGENTS.md — danielnachumdev/actions

Implementation guide for maintainers and coding agents changing **this** repo.  
Pitch / consumer quickstart: [`README.md`](README.md). Adoption checklist: [`HOW-TO-USE.md`](HOW-TO-USE.md).

---

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + templates; **also a consumer** of those blocks |
| Toolchain | [uv](https://docs.astral.sh/uv/) + `pyproject.toml` / `uv.lock` (test harness only — not published) |
| Python | `>=3.11` (CI matrix **3.11, 3.12, 3.13** via reusable `ci.yml` defaults) |
| Tests | `tests/` — pytest; **never delete** |
| Workflows | **Flat** under `.github/workflows/` (no subdirs — GitHub rule) |
| Building blocks | `ci.yml` (umbrella Detect), `python.yml`, `node.yml`, `github-yaml.yml`, `rebase-guard.yml`, `terraform-validate.yml`, `terraform.yml`, `semver-ci.yml`, `semver-cd.yml`, `retag.yml`, `dependabot-auto-merge.yml`, `validate-skills.yml`, `cloudrun-deploy.yml`, `raft-deploy.yml` |
| Detect | `scripts/ci/detect_layout.sh` (+ bundled copy under `.github/actions/detect-layout/`); umbrella checks out standards at `standards-ref` |
| Dogfood | Thin `check.yml` (`name: CI`) + `cd.yml` call `./.github/workflows/…`; dogfood passes `standards-ref: ${{ github.sha }}` |
| Pinning (consumers) | Prefer **`@latest`** (CD opts into `retags: '["latest"]'`); immutable `@vN.N.N` to freeze |
| Semver labels | Exactly one of: `noBump` \| `bumpPatch` \| `bumpMinor` \| `bumpMajor` |
| Secrets | Never commit API tokens, `.pypirc`, or credential files. Thin CD may map `PYPI_API_TOKEN` by name (needed for `publish-pypi: true`; empty OK when PyPI-off / OIDC is caller-inlined). |
| Issue templates | [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/) — feature request + bug report; blank issues allowed |

```text
.
├── .github/
│   ├── CODEOWNERS
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/          # feature_request + bug_report + config.yml
│   ├── actions/detect-layout/   # composite + bundled detect_layout.sh
│   └── workflows/
│       ├── ci.yml               # umbrella Detect → lanes → aggregate CI
│       ├── python.yml           # uv pytest matrix lane
│       ├── node.yml             # Node/TS lint+test matrix lane
│       ├── github-yaml.yml      # parse .github/**/*.yml
│       ├── rebase-guard.yml     # Alembic revision rebase check
│       ├── terraform-validate.yml  # fmt + init -backend=false + validate
│       ├── terraform.yml        # WIF → fmt/init/plan; apply post-merge by default
│       ├── semver-ci.yml        # CI stage: validate bump label on PR
│       ├── semver-cd.yml        # CD: bump → wheel → Release → optional retag → optional PyPI
│       ├── retag.yml            # force-move explicit floating tags
│       ├── dependabot-auto-merge.yml
│       ├── validate-skills.yml  # opt-in skills-ref + Cursor allowlist
│       ├── cloudrun-deploy.yml  # WIF → gcloud builds triggers run + stream logs
│       ├── raft-deploy.yml      # SSH + raft apply / doctor on a VPS
│       ├── check.yml            # dogfood thin CI (name: CI)
│       └── cd.yml               # dogfood thin CD
├── scripts/ci/detect_layout.sh  # Detect source of truth (keep action copy in sync)
├── scripts/validate_skills.sh   # Agent Skills validator launcher (pinned skills-ref)
├── scripts/validate_skills.py
├── scripts/release/             # release_semver.py, build_python_uv_wheel.sh
├── templates/                   # consumer copy-paste CI/CD/retag/cloudrun/raft/terraform/skills + CODEOWNERS / Dependabot (@latest)
├── examples/
├── tests/
├── pyproject.toml               # test harness (danielnachumdev-actions-tests); not on PyPI
├── README.md                    # Marketing / consumer pitch
├── HOW-TO-USE.md                # Consumer adoption checklist
└── AGENTS.md                    # This file
```

There is **one semver feature**. `semver-ci` and `semver-cd` are the same rules at different pipeline stages — not a separate “label” product.

Reusable `ci.yml` must **not** self-trigger on push/PR (that would collide with the thin orchestrator filename pattern and skip dogfooding). Triggers live only on thin `check.yml` / consumer `ci.yml`.

---

## Develop this repo

```bash
uv sync                 # runtime only → .venv (none today)
uv sync --group dev     # + pytest, pyyaml
# or: uv sync --all-groups
```

`tool.uv.default-groups` is empty — `uv sync` does **not** install `dev` by default.

| Task | Command |
| ---- | ------- |
| Tests | `uv run pytest -q` |
| Semver script smoke | `uv run python scripts/release/release_semver.py --latest-tag v1.2.3 --label bumpPatch` |

Config for pytest lives in `pyproject.toml`. Prefer editing floors / deps there and regenerating with `uv lock` / `uv sync --group dev`.

### Changing CI / workflows

1. Edit reusable blocks under `.github/workflows/` and Detect under `scripts/ci/detect_layout.sh` (copy into `.github/actions/detect-layout/detect_layout.sh`).
2. Keep dogfood thin `check.yml` / `cd.yml` aligned with [`templates/workflows/`](templates/workflows/) (relative `./` here; `@latest` in templates). Cloud Run stays direct-call only.
3. Update [`HOW-TO-USE.md`](HOW-TO-USE.md) + templates when inputs, required check names, or adoption steps change.
4. Breaking inputs / check names → new **major** tag; update templates + consumers together.
5. Umbrella Detect checks out this repo at `standards-ref` into `.actions-standards` then `uses: ./.actions-standards/.github/actions/detect-layout` (relative `./.github/actions` from `workflow_call` would resolve to the **caller**).

---

## Consumer pins (contract reference)

```yaml
# CI — tests + semver label gate
jobs:
  ci:
    name: CI
    uses: danielnachumdev/actions/.github/workflows/ci.yml@latest
    # with:
    #   python-versions: '["3.11","3.12","3.13"]'
    #   python-versions-push: '["3.11","3.13"]'   # lighter post-merge
    #   skip-node-push: true
  semver:
    name: Semver
    if: github.event_name == 'pull_request'
    uses: danielnachumdev/actions/.github/workflows/semver-ci.yml@latest
    with:
      standards-ref: latest
```

```yaml
# CD — after successful CI on main
permissions:
  contents: write
  # id-token: write  # only if you inline Trusted Publishing in this workflow
jobs:
  semver:
    name: Semver
    uses: danielnachumdev/actions/.github/workflows/semver-cd.yml@latest
    with:
      standards-ref: latest
      sha: ${{ github.event.workflow_run.head_sha }}
      # publish-pypi: true  # token path (requires PYPI_API_TOKEN)
      # Opt-in floating tags (empty/omit = no retag job):
      retags: '["latest"]'
    secrets:
      # User repos: map by name (inherit is org/enterprise only). Empty OK when PyPI-off.
      PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }}
```

Soft-protect with the check names a green PR in **that** consumer actually reports (this hub’s thin umbrella shape → usually **`CI / CI`** + **`Semver / Semver`** when Semver is adopted). Custom multi-lane aggregates often report plain **`CI`**. See HOW-TO-USE.md → Required check names — never copy a name without confirming.

Include PR types `labeled` / `unlabeled` on the consumer CI workflow so label edits re-run `semver-ci`.

### `ci.yml` inputs (optional)

Detect auto-selects lanes from layout under `working-directory`. Credentials unlock deploy-ish lanes (Terraform apply, raft). See HOW-TO-USE detection table.

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `working-directory` | `.` | Scoped marker root |
| `standards-ref` | `latest` | Ref of this hub for detect-layout checkout |
| `python-versions` | `["3.11","3.12","3.13"]` | Matrix JSON (both events) |
| `node-versions` | `""` | Empty → infer `.nvmrc` / engines / `["20","22"]` |
| `sync-args` | `""` | Empty → infer from pyproject dependency groups |
| `pytest-command` | `pytest -q` | Full invocation under `uv run` |
| `workload_identity_provider` / `service_account` | `""` | Non-empty → terraform plan/apply when TF layout present |
| `raft-service` / `raft-git-repo` | `""` | With `secrets.VPS_SSH_KEY` + `.raft/` → raft lane |
| `disable-*` / `allow-empty` | `false` | Force-skip lanes / empty OK |
| lane `*-timeout-minutes` | (see HOW-TO-USE) | Per-lane timeouts |

Optional post-merge: `python-versions-push`, `node-versions-push`, `sync-args-push`, `skip-python-push`, `skip-node-push`. Omitted/`""` inherits shared (does **not** clear). Consumers must **not** inject `github.event_name` for matrices.

### `semver-cd.yml` inputs

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `sha` | required | Commit to tag / release |
| `standards-ref` | `v1` | Ref for scripts checkout; templates pass `latest` to match `@latest` pins |
| `dry-run` | `false` | Resolve only |
| `build-command` | (default wheel script) | Must print `wheel=<path>`; `TAG` in env |
| `python-version` / `latest-tag-override` | `3.13` / empty | Build Python / force latest tag |
| `publish-pypi` | `false` | Upload release wheel to PyPI via **API token** only |
| `retags` | `""` | JSON array of floating tags to force-move after release; `""` / `[]` = no-op |
| `timeout-minutes` | `30` | Semver job (bump / build / release) |
| `pypi-timeout-minutes` | `15` | Opt-in PyPI publish job |
| `retag-timeout-minutes` | `10` | Passed to `retag.yml` |


### `retag.yml` inputs (standalone or via `semver-cd`)

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `sha` | required | Commit floating tags should point at |
| `tags` | `["latest"]` | JSON array of tag names to force-move |
| `dry-run` | `false` | Print planned moves only |
| `timeout-minutes` | `10` | Retag job timeout |

Caller needs `permissions: contents: write`. Only moves tags listed in `tags`.

### `cloudrun-deploy.yml` inputs

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `workload_identity_provider` | required | Full WIF provider resource name |
| `service_account` | required | GCP SA email to impersonate |
| `gcp_project` | required | Project owning the Cloud Build trigger |
| `trigger` | required | Cloud Build trigger id or name |
| `sha` | required | Commit SHA to deploy |
| `trigger_region` | `""` | Regional trigger; empty omits `--region` (global) |
| `timeout-minutes` | `45` | Deploy job timeout |

Caller needs `permissions: id-token: write` (+ `contents: read` as needed). Path filters / GHCR / raft stay in the caller. WIF pools should usually trust the **calling** repo (`attribute.repository`), not PyPI-style `job_workflow_ref` binding to this reusable file.

### `terraform.yml` inputs

| Input | Default | Meaning |
| ----- | ------- | ------- |
| `workload_identity_provider` | required | Full WIF provider resource name |
| `service_account` | required | GCP SA email to impersonate |
| `working-directory` | `terraform` | Terraform root module directory |
| `terraform-version` | `1.9.8` | CLI version for `hashicorp/setup-terraform` |
| `ref` | `""` | Optional checkout ref; empty → default checkout |
| `init-args` / `plan-args` | `""` | Extra CLI args for init / plan |
| `apply` | `false` | Force apply (including on `pull_request`) |
| `skip-apply-push` | `false` | Plan-only on `push`; `workflow_dispatch` still applies |
| `skip-fmt` | `false` | Skip `terraform fmt -check -recursive` |
| `timeout-minutes` | `30` | Terraform job timeout |

Default lifecycle: **plan on every call**; **apply** on `push` / `workflow_dispatch` (not on `pull_request` unless `apply: true`). When applying, plan uses `-out=tfplan` and apply consumes that file. Caller needs `permissions: id-token: write`. Same WIF calling-repo trust note as `cloudrun-deploy`.

### `semver-cd.yml` secrets

| Secret | Required | Meaning |
| ------ | -------- | ------- |
| `PYPI_API_TOKEN` | no | Required when `publish-pypi: true`; unused when PyPI-off or Trusted Publishing is caller-inlined |

Callers **must**:
1. Pass `secrets: { PYPI_API_TOKEN: ${{ secrets.PYPI_API_TOKEN }} }` — user repos cannot use `secrets: inherit` (org/enterprise only).
2. For **Trusted Publishing**, keep `publish-pypi: false` and inline a `pypi` job in thin `cd.yml` with `permissions.id-token: write` (see HOW-TO-USE). Do not expect OIDC to work from this reusable PyPI job ([warehouse#11096](https://github.com/pypi/warehouse/issues/11096)).

An unset token is fine (`required: false`) when PyPI-off / caller-inlined OIDC.

On a successful release, when `retags` is non-empty, `semver-cd` calls `retag.yml` with that list as `tags`. Empty `retags` (`""` or `[]`) skips the retag job. PyPI stays `needs: [semver]` only (parallel with retag). When `publish-pypi: true`, the **PyPI** job downloads that release’s `.whl` and runs `uv publish --token` (`PYPI_API_TOKEN` required). This repo’s dogfood `cd.yml` leaves PyPI **off** and opts into `retags: '["latest"]'`.

---

## Pitfalls

1. No `.github/workflows/**/subdirs` for reusable workflows.
2. `uses: ./.github/actions/...` inside `workflow_call` resolves to the **caller** — use full `danielnachumdev/actions/...@latest` or inline (as `ci.yml` detect does).
3. `uses:` must be a literal string.
4. No `${{ secrets.* }}` inside `workflow_call` `description:` fields.
5. On **this** repo, thin CI cannot be named `ci.yml` (that file is the reusable block) — use `check.yml` with `name: CI`.

---

## PRs, CI, and releases

1. Branch off `main`; open a PR into `main`.
2. Attach **exactly one** semver label: `noBump` | `bumpPatch` | `bumpMinor` | `bumpMajor`.
3. **CI** — dogfood `check.yml` → reusable `ci.yml` + `semver-ci.yml`. This repo’s green PRs report **`CI / CI`** and **`Semver / Semver`** (require those here). Consumers: match whatever *their* PR reports — see HOW-TO-USE.md → Required check names.
4. **CD** — dogfood `cd.yml` → `semver-cd.yml` after CI succeeds on `main`: bump → wheel → GitHub Release → optional `retags` → optional PyPI, or skip on `noBump`.
5. Version **source of truth** is GitHub Release tags (optional floating `latest` when CD `retags` are enabled).
6. Dependabot PRs stay on `noBump`.
7. Docs-only / non-release changes use `noBump`.

### Repo gates (already configured)

- `.github/CODEOWNERS` — `@danielnachumdev`
- Required checks for **this** dogfood shape: **`CI / CI`** + **`Semver / Semver`**; code-owner reviews; no force-push to `main`
- Private vulnerability reporting via GitHub Security Advisories when enabled

---

## Sensitive / ignored

Do not commit: `.pypirc`, API tokens, credential JSON, `.venv/`, `venv/`, `dist/`, `__pycache__/`, `.actions-standards/`. Track `uv.lock`. Respect `.gitignore`.
