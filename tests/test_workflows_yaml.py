"""Smoke-parse reusable workflow YAML and assert key surfaces exist."""

from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_TEMPLATES = _ROOT / "templates" / "workflows"


def _load(name: str, *, templates: bool = False) -> dict:
    path = (_TEMPLATES if templates else _WORKFLOWS) / name
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict), name
    return data


def _on(data: dict) -> dict:
    # PyYAML 1.1 treats bare key `on` as boolean True.
    block = data.get("on", data.get(True))
    assert isinstance(block, dict), "missing workflow on: block"
    return block


def _assert_timeout_input(inputs: dict, key: str) -> None:
    """Timeout knobs are policy: require a positive numeric default, not a fixed value."""
    assert key in inputs, key
    assert inputs[key]["type"] == "number", key
    default = inputs[key]["default"]
    assert isinstance(default, int), key
    assert default > 0, key


def _input_expr(input_key: str) -> str:
    return "${{ inputs.%s }}" % input_key


def _assert_job_timeout_wired(job: dict, input_key: str) -> None:
    assert "timeout-minutes" in job, job.get("name", job)
    assert job["timeout-minutes"] == _input_expr(input_key)


def _assert_with_timeout_wired(with_block: dict, input_key: str) -> None:
    assert "timeout-minutes" in with_block
    assert with_block["timeout-minutes"] == _input_expr(input_key)


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

    def test_timeout_inputs_wired_to_jobs(self):
        data = _load("ci.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        for key in (
            "detect-timeout-minutes",
            "python-timeout-minutes",
            "node-timeout-minutes",
            "ci-timeout-minutes",
        ):
            _assert_timeout_input(inputs, key)
        jobs = data["jobs"]
        _assert_job_timeout_wired(jobs["detect"], "detect-timeout-minutes")
        _assert_job_timeout_wired(jobs["ci"], "ci-timeout-minutes")
        _assert_with_timeout_wired(jobs["python"]["with"], "python-timeout-minutes")
        _assert_with_timeout_wired(jobs["node"]["with"], "node-timeout-minutes")


class TestPythonWorkflow:
    def test_timeout_input_wired(self):
        data = _load("python.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        _assert_timeout_input(inputs, "timeout-minutes")
        _assert_job_timeout_wired(data["jobs"]["test"], "timeout-minutes")


class TestNodeWorkflow:
    def test_timeout_input_wired(self):
        data = _load("node.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        _assert_timeout_input(inputs, "timeout-minutes")
        _assert_job_timeout_wired(data["jobs"]["test"], "timeout-minutes")


class TestSemverCiWorkflow:
    def test_timeout_input_wired(self):
        data = _load("semver-ci.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        _assert_timeout_input(inputs, "timeout-minutes")
        _assert_job_timeout_wired(data["jobs"]["semver"], "timeout-minutes")

    def test_hardens_standards_ref_checkout(self):
        """workflow_dispatch callers can write default-branch cache; guard first."""
        data = _load("semver-ci.yml")
        steps = data["jobs"]["semver"]["steps"]
        by_name = {
            s["name"]: s for s in steps if isinstance(s, dict) and "name" in s
        }
        assert "Guard standards ref" in by_name
        guard_run = by_name["Guard standards ref"]["run"]
        assert "STANDARDS_REPO" in by_name["Guard standards ref"]["env"]
        assert "danielnachumdev/actions" in by_name["Guard standards ref"]["env"][
            "STANDARDS_REPO"
        ]
        assert "v[0-9]+" in guard_run
        assert "0-9a-f" in guard_run
        assert 'repos/${STANDARDS_REPO}/commits/${REF}' in guard_run
        standards = by_name["Checkout standards"]
        assert standards["with"]["ref"] == "${{ inputs.standards-ref }}"
        assert standards["with"]["persist-credentials"] is False
        names = [s.get("name", "") for s in steps if isinstance(s, dict)]
        assert names.index("Guard standards ref") < names.index("Checkout standards")


class TestRetagWorkflow:
    def test_parses_and_requires_sha(self):
        data = _load("retag.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        assert inputs["sha"]["required"] is True
        assert inputs["tags"]["default"] == '["latest"]'
        assert "move-latest" not in inputs
        assert "release-tag" not in inputs
        assert set(inputs) == {"sha", "tags", "dry-run", "timeout-minutes"}
        assert "retag" in data["jobs"]

    def test_timeout_input_wired(self):
        data = _load("retag.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        _assert_timeout_input(inputs, "timeout-minutes")
        _assert_job_timeout_wired(data["jobs"]["retag"], "timeout-minutes")


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

    def test_timeout_inputs_wired_to_jobs(self):
        data = _load("semver-cd.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        for key in (
            "timeout-minutes",
            "pypi-timeout-minutes",
            "retag-timeout-minutes",
        ):
            _assert_timeout_input(inputs, key)
        jobs = data["jobs"]
        _assert_job_timeout_wired(jobs["semver"], "timeout-minutes")
        _assert_job_timeout_wired(jobs["pypi"], "pypi-timeout-minutes")
        _assert_with_timeout_wired(jobs["retag"]["with"], "retag-timeout-minutes")

    def test_hardens_privileged_sha_checkout(self):
        """workflow_run CD may call this; checkout must not persist write creds."""
        data = _load("semver-cd.yml")
        steps = data["jobs"]["semver"]["steps"]
        by_name = {
            s["name"]: s for s in steps if isinstance(s, dict) and "name" in s
        }
        assert "Guard release SHA" in by_name
        guard_run = by_name["Guard release SHA"]["run"]
        assert "compare/main..." in guard_run
        assert "identical|behind" in guard_run
        caller = by_name["Checkout caller at SHA"]
        assert caller["with"]["ref"] == "${{ inputs.sha }}"
        assert caller["with"]["persist-credentials"] is False
        standards = by_name["Checkout standards"]
        assert standards["with"]["persist-credentials"] is False
        # Guard runs before any checkout of inputs.sha.
        names = [s.get("name", "") for s in steps if isinstance(s, dict)]
        assert names.index("Guard release SHA") < names.index(
            "Checkout caller at SHA"
        )


class TestDogfoodCdWorkflow:
    def test_opts_into_latest_retags(self):
        data = _load("cd.yml")
        jobs = data["jobs"]
        assert "semver" in jobs
        with_block = jobs["semver"]["with"]
        assert with_block["retags"] == '["latest"]'
        assert "move-latest" not in with_block
        assert "floating-tags" not in with_block

    def test_workflow_run_limited_to_main(self):
        data = _load("cd.yml")
        trigger = _on(data)["workflow_run"]
        assert trigger["branches"] == ["main"]
        job_if = data["jobs"]["semver"]["if"]
        assert "workflow_run.event == 'push'" in job_if
        assert "head_branch == 'main'" in job_if

    def test_template_cd_matches_dogfood_workflow_run_guard(self):
        data = _load("cd.yml", templates=True)
        assert _on(data)["workflow_run"]["branches"] == ["main"]
        job_if = data["jobs"]["semver"]["if"]
        assert "workflow_run.event == 'push'" in job_if
        assert "head_branch == 'main'" in job_if
