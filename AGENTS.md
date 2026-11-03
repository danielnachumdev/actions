# AGENTS.md — danielnachumdev/actions

Consume docs: [`README.md`](README.md). Rollout: [`PLAYBOOK.md`](PLAYBOOK.md).

## Orientation

| Item | Detail |
| ---- | ------ |
| Role | Shared reusable workflows + release scripts + templates |
| Workflow layout | **Flat** under `.github/workflows/` only (GitHub rule) |
| Short names | `ci.yml`, `python.yml`, `label.yml`, `release.yml` |
| Actions | Folders OK under `.github/actions/<name>/` |
| Pinning | Callers use **`@v1`** |

## Layout

```text
.github/workflows/ci.yml       # public CI entry (+ dogfood)
.github/workflows/python.yml   # uv pytest matrix lane
.github/workflows/label.yml    # release-label gate
.github/workflows/release.yml  # semver GitHub Release
.github/actions/detect-layout/ # optional composite (prefer inline in ci.yml for workflow_call)
scripts/release/
templates/
examples/
```

## Critical: relative actions in reusable workflows

`uses: ./.github/actions/...` inside a `workflow_call` workflow resolves against the **caller** repository. Use a fully qualified `danielnachumdev/actions/.github/actions/…@v1` or **inline** the step (as `ci.yml` does).

## Develop

```bash
uv sync --group dev
uv run pytest -q
```

Breaking check names or inputs → new major tag; update templates + playbook in the same PR.
