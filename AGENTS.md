# AGENTS.md — danielnachumdev/actions

Guide for changing **this** standards repo. User-facing consume docs: [`README.md`](README.md). Rollout checklist: [`PLAYBOOK.md`](PLAYBOOK.md).

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + templates |
| Python | `>=3.11` (test harness only; not a published package) |
| Pinning | Callers must use **tags** (`@v1`); breaking changes → `v2` |
| Do not | Put product-specific SPA/e2e/path-filter logic here |

## Layout

```text
.github/workflows/     # reusable-*.yml (+ CI for this repo)
scripts/release/       # release_semver.py, build_python_uv_wheel.sh
templates/             # copy-paste starters for product repos
examples/              # oriented walkthroughs (python-uv-library)
tests/                 # pytest for release_semver
PLAYBOOK.md            # generalize & apply to other repos
```

## Develop

```bash
uv sync --group dev
uv run pytest -q
```

When changing reusable workflow **inputs** in a breaking way, cut a new major tag and update `templates/` + `PLAYBOOK.md` in the same PR.

## Release this repo

Use the same label rules as consumers (`bumpMajor` / `bumpMinor` / `bumpPatch` / `noBump`).  
Tagging strategy for callers: keep a moving major tag `v1` pointing at the latest compatible release, or document `v1.x.y` pins only.

## PR requirements

Exactly one release label. Do not break `@v1` callers without a major bump and playbook note.
