"""Smoke-parse reusable workflow YAML and assert key surfaces exist."""

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"


def _load(name: str) -> dict:
    path = _WORKFLOWS / name
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), name
    return data


def _on(data: dict) -> dict:
    # PyYAML 1.1 treats bare key `on` as boolean True.
    block = data.get("on", data.get(True))
    assert isinstance(block, dict), "missing workflow on: block"
    return block


class TestCiWorkflow:
    def test_parses_and_exposes_event_knobs(self):
        data = _load("ci.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        for key in (
            "python-versions",
            "python-versions-push",
            "node-versions",
            "node-versions-push",
            "sync-args",
            "sync-args-push",
            "pytest-args",
            "pytest-args-push",
            "skip-python-push",
            "skip-node-push",
            "disable-python",
            "disable-node",
            "allow-empty",
        ):
            assert key in inputs, key
        # No pre-merge-only overrides — shared defaults cover pull_request.
        for key in list(inputs):
            assert not key.endswith("-pr"), key
            assert not key.startswith("skip-") or key.endswith("-push"), key
        assert inputs["python-versions-push"]["default"] == ""
        assert inputs["skip-python-push"]["default"] is False
        jobs = data["jobs"]
        assert "detect" in jobs and "python" in jobs and "node" in jobs and "ci" in jobs
        detect_outputs = jobs["detect"]["outputs"]
        for key in ("python_versions", "node_versions", "sync_args", "pytest_args"):
            assert key in detect_outputs, key


class TestRetagWorkflow:
    def test_parses_and_requires_sha(self):
        data = _load("retag.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        assert inputs["sha"]["required"] is True
        assert inputs["tags"]["default"] == '["latest"]'
        assert "move-major" not in inputs
        assert "release-tag" not in inputs
        assert set(inputs) == {"sha", "tags", "dry-run"}
        assert "retag" in data["jobs"]


class TestSemverCdWorkflow:
    def test_parses_and_wires_retag(self):
        data = _load("semver-cd.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        assert "move-latest" not in inputs
        assert "floating-tags" not in inputs
        assert "move-major" not in inputs
        assert inputs["retags"]["default"] == ""
        jobs = data["jobs"]
        assert "retag" in jobs
        assert jobs["retag"]["needs"] == ["semver"]
        assert jobs["retag"]["uses"] == "./.github/workflows/retag.yml"
        retag_if = jobs["retag"]["if"]
        assert "inputs.retags != ''" in retag_if
        assert "inputs.retags != '[]'" in retag_if
        assert "move-latest" not in retag_if
        retag_with = jobs["retag"]["with"]
        assert "move-major" not in retag_with
        assert "release-tag" not in retag_with
        assert retag_with["tags"] == "${{ inputs.retags }}"
        # PyPI stays parallel with retag (needs semver only).
        assert jobs["pypi"]["needs"] == ["semver"]
        semver_steps = jobs["semver"]["steps"]
        step_names = [s.get("name", "") for s in semver_steps if isinstance(s, dict)]
        assert "Move floating major tag" not in step_names


class TestDogfoodCdWorkflow:
    def test_opts_into_latest_retags(self):
        data = _load("cd.yml")
        jobs = data["jobs"]
        assert "semver" in jobs
        with_block = jobs["semver"]["with"]
        assert with_block["retags"] == '["latest"]'
        assert "move-latest" not in with_block
        assert "floating-tags" not in with_block
