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
            "pytest-command",
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
        assert inputs["pytest-command"]["default"] == "pytest -q"
        assert "pytest-command-push" not in inputs
        assert inputs["skip-python-push"]["default"] is False
        jobs = data["jobs"]
        assert "detect" in jobs and "python" in jobs and "node" in jobs and "ci" in jobs
        detect_outputs = jobs["detect"]["outputs"]
        for key in (
            "python_versions",
            "node_versions",
            "sync_args",
            "pytest_command",
        ):
            assert key in detect_outputs, key
        python_with = jobs["python"]["with"]
        assert python_with["pytest-command"] == (
            "${{ needs.detect.outputs.pytest_command }}"
        )
        assert "pytest-args" not in python_with

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

    def test_pytest_command_defaults_and_wired(self):
        data = _load("python.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        assert inputs["pytest-command"]["default"] == "pytest -q"
        assert "pytest-args" not in inputs
        steps = data["jobs"]["test"]["steps"]
        pytest_step = next(
            s for s in steps if isinstance(s, dict) and s.get("name") == "Pytest"
        )
        assert pytest_step["run"] == "uv run ${{ inputs.pytest-command }}"
        assert data["jobs"]["test"]["defaults"]["run"]["working-directory"] == (
            "${{ inputs.working-directory }}"
        )


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

    def test_pypi_job_is_token_only(self):
        """Reusable PyPI job uses API token; Trusted Publishing is caller-inlined."""
        data = _load("semver-cd.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        assert "pypi-auth" not in inputs
        pypi = data["jobs"]["pypi"]
        assert "id-token" not in pypi.get("permissions", {})
        steps = pypi["steps"]
        by_name = {
            s["name"]: s for s in steps if isinstance(s, dict) and "name" in s
        }
        publish = by_name["Publish to PyPI"]
        assert "PYPI_AUTH" not in publish.get("env", {})
        run = publish["run"]
        assert "--token" in run
        assert "--trusted-publishing" not in run
        assert "warehouse#11096" in run


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


class TestRaftDeployWorkflow:
    def test_parses_required_inputs_and_secret(self):
        data = _load("raft-deploy.yml")
        call = _on(data)["workflow_call"]
        inputs = call["inputs"]
        for key in ("service", "git-repo", "ref"):
            assert inputs[key]["required"] is True, key
        assert inputs["host"]["default"] == ""
        assert inputs["ssh-user"]["default"] == ""
        assert inputs["command_timeout"]["default"] == "10m"
        assert inputs["skip-doctor"]["default"] is False
        _assert_timeout_input(inputs, "timeout-minutes")
        assert call["secrets"]["VPS_SSH_KEY"]["required"] is True
        assert set(inputs) == {
            "service",
            "git-repo",
            "ref",
            "host",
            "ssh-user",
            "command_timeout",
            "skip-doctor",
            "timeout-minutes",
        }

    def test_timeout_wired_and_ssh_script(self):
        data = _load("raft-deploy.yml")
        job = data["jobs"]["apply"]
        _assert_job_timeout_wired(job, "timeout-minutes")
        steps = job["steps"]
        by_name = {
            s["name"]: s for s in steps if isinstance(s, dict) and "name" in s
        }
        resolve = by_name["Resolve SSH target"]
        assert "vars.VPS_HOST" in resolve["env"]["VAR_HOST"]
        assert "vars.VPS_USER" in resolve["env"]["VAR_USER"]
        assert "::error::" in resolve["run"]
        assert "VPS_SSH_KEY" in resolve["run"]
        assert "VPS_HOST" in resolve["run"]
        ssh = by_name["Apply App + redeploy on VPS"]
        assert ssh["uses"] == "appleboy/ssh-action@v1.2.0"
        assert ssh["with"]["command_timeout"] == "${{ inputs.command_timeout }}"
        assert ssh["with"]["key"] == "${{ secrets.VPS_SSH_KEY }}"
        script = ssh["with"]["script"]
        assert 'raft auth test "${SERVICE}" --repo "${GIT_REPO}"' in script
        assert 'raft apply --git "${GIT_REPO}" --ref "${REF}"' in script
        assert 'raft doctor "${SERVICE}"' in script
        assert "SKIP_DOCTOR" in script

    def test_template_calls_reusable(self):
        data = _load("raft-deploy.yml", templates=True)
        job = data["jobs"]["apply"]
        assert (
            job["uses"]
            == "danielnachumdev/actions/.github/workflows/raft-deploy.yml@latest"
        )
        assert "service" in job["with"]
        assert "git-repo" in job["with"]
        assert "ref" in job["with"]
        assert job["secrets"]["VPS_SSH_KEY"] == "${{ secrets.VPS_SSH_KEY }}"
        howto = (_ROOT / "HOW-TO-USE.md").read_text(encoding="utf-8")
        assert "### Raft VPS apply / redeploy (optional)" in howto
        assert "raft-deploy.yml@latest" in howto
        assert "vars.VPS_HOST" in howto


class TestTerraformWorkflow:
    def test_parses_required_inputs_and_defaults(self):
        data = _load("terraform.yml")
        assert "workflow_call" in _on(data)
        inputs = _on(data)["workflow_call"]["inputs"]
        for key in ("workload_identity_provider", "service_account"):
            assert inputs[key]["required"] is True, key
        assert inputs["working-directory"]["default"] == "terraform"
        assert inputs["terraform-version"]["default"] == "1.9.8"
        assert inputs["ref"]["default"] == ""
        assert inputs["init-args"]["default"] == ""
        assert inputs["plan-args"]["default"] == ""
        assert inputs["apply"]["default"] is False
        assert inputs["skip-apply-push"]["default"] is False
        assert inputs["skip-fmt"]["default"] is False
        _assert_timeout_input(inputs, "timeout-minutes")
        assert inputs["timeout-minutes"]["default"] == 30
        assert set(inputs) == {
            "workload_identity_provider",
            "service_account",
            "working-directory",
            "terraform-version",
            "ref",
            "init-args",
            "plan-args",
            "apply",
            "skip-apply-push",
            "skip-fmt",
            "timeout-minutes",
        }
        perms = data["permissions"]
        assert perms["id-token"] == "write"
        assert perms["contents"] == "read"

    def test_plan_always_apply_gated_and_timeout_wired(self):
        data = _load("terraform.yml")
        job = data["jobs"]["terraform"]
        _assert_job_timeout_wired(job, "timeout-minutes")
        assert job["defaults"]["run"]["working-directory"] == (
            "${{ inputs.working-directory }}"
        )
        assert job["env"]["TF_IN_AUTOMATION"] == "true"
        steps = job["steps"]
        by_name = {
            s["name"]: s for s in steps if isinstance(s, dict) and "name" in s
        }
        assert "Authenticate to Google Cloud" in by_name
        assert by_name["Authenticate to Google Cloud"]["uses"].startswith(
            "google-github-actions/auth@"
        )
        assert by_name["Setup Terraform"]["uses"].startswith(
            "hashicorp/setup-terraform@"
        )
        assert by_name["Setup Terraform"]["with"]["terraform_wrapper"] is False
        assert by_name["Terraform fmt"]["run"] == (
            "terraform fmt -check -recursive"
        )
        assert "skip-fmt" in by_name["Terraform fmt"]["if"]
        plan = by_name["Terraform plan"]
        assert "terraform plan" in plan["run"]
        assert "-out=tfplan" in plan["run"]
        assert "DO_APPLY" in plan["env"]
        apply = by_name["Terraform apply"]
        apply_if = apply["if"]
        assert "inputs.apply" in apply_if
        assert "workflow_dispatch" in apply_if
        assert "skip-apply-push" in apply_if
        assert "pull_request" not in apply_if
        assert apply["run"] == (
            "terraform apply -auto-approve -input=false tfplan"
        )

    def test_template_pins_v1_and_howto_documents_lifecycle(self):
        text = (_TEMPLATES / "terraform.yml").read_text(encoding="utf-8")
        assert "terraform.yml@latest" in text
        assert "id-token: write" in text
        assert "pull_request" in text
        data = _load("terraform.yml", templates=True)
        job = data["jobs"]["terraform"]
        assert job["uses"].endswith("terraform.yml@latest")
        assert "workload_identity_provider" in job["with"]
        assert "service_account" in job["with"]
        howto = (_ROOT / "HOW-TO-USE.md").read_text(encoding="utf-8")
        assert "### Terraform plan / apply (optional)" in howto
        assert "terraform.yml@latest" in howto
        assert "skip-apply-push" in howto
        assert "plan only" in howto.lower() or "plan-only" in howto.lower()
        assert "attribute.repository" in howto


class TestCloudrunDeployWorkflow:
    def test_parses_and_requires_core_inputs(self):
        data = _load("cloudrun-deploy.yml")
        assert "workflow_call" in _on(data)
        inputs = _on(data)["workflow_call"]["inputs"]
        for key in (
            "workload_identity_provider",
            "service_account",
            "gcp_project",
            "trigger",
            "sha",
        ):
            assert inputs[key]["required"] is True, key
        assert inputs["trigger_region"]["default"] == ""
        assert set(inputs) == {
            "workload_identity_provider",
            "service_account",
            "gcp_project",
            "trigger",
            "sha",
            "trigger_region",
            "timeout-minutes",
        }
        perms = data["permissions"]
        assert perms["id-token"] == "write"
        assert perms["contents"] == "read"
        jobs = data["jobs"]
        assert "deploy" in jobs
        steps = jobs["deploy"]["steps"]
        by_name = {
            s["name"]: s for s in steps if isinstance(s, dict) and "name" in s
        }
        assert "Authenticate to Google Cloud" in by_name
        assert by_name["Authenticate to Google Cloud"]["uses"].startswith(
            "google-github-actions/auth@"
        )
        assert by_name["Set up Cloud SDK"]["uses"].startswith(
            "google-github-actions/setup-gcloud@"
        )
        run = by_name["Run Cloud Build deploy trigger"]["run"]
        assert "gcloud builds triggers run" in run
        assert "gcloud builds log" in run
        assert "--stream" in run
        assert "--sha=" in run

    def test_timeout_input_wired(self):
        data = _load("cloudrun-deploy.yml")
        inputs = _on(data)["workflow_call"]["inputs"]
        _assert_timeout_input(inputs, "timeout-minutes")
        assert inputs["timeout-minutes"]["default"] == 45
        _assert_job_timeout_wired(data["jobs"]["deploy"], "timeout-minutes")

    def test_template_pins_v1_and_documents_permissions(self):
        text = (_TEMPLATES / "cloudrun-deploy.yml").read_text(encoding="utf-8")
        assert "cloudrun-deploy.yml@latest" in text
        assert "id-token: write" in text
        data = _load("cloudrun-deploy.yml", templates=True)
        job = data["jobs"]["deploy"]
        assert job["uses"].endswith("cloudrun-deploy.yml@latest")
        assert "sha" in job["with"]
        assert "workload_identity_provider" in job["with"]
        assert "service_account" in job["with"]
        assert "gcp_project" in job["with"]
        assert "trigger" in job["with"]

    def test_howto_documents_wif_caveat(self):
        howto = (_ROOT / "HOW-TO-USE.md").read_text(encoding="utf-8")
        assert "cloudrun-deploy.yml@latest" in howto
        assert "job_workflow_ref" in howto
        assert "attribute.repository" in howto



class TestDependabotAutoMergeWorkflow:
    def test_is_reusable_workflow_call(self):
        data = _load("dependabot-auto-merge.yml")
        assert "workflow_call" in _on(data)
        assert "pull_request" not in _on(data)
        jobs = data["jobs"]
        assert "merge" in jobs
        merge_job = jobs["merge"]
        assert merge_job["name"] == "Merge"
        assert "Enable" not in merge_job["name"]
        merge_if = merge_job["if"]
        assert "dependabot[bot]" in merge_if
        step = merge_job["steps"][0]
        assert step["name"] == "Merge Dependabot PR"
        assert "Enable" not in step["name"]
        assert step["env"]["EXPECTED_SHA"] == "${{ github.event.pull_request.head.sha }}"
        step_run = step["run"]
        assert "gh pr diff \"$PR_URL\" --name-only" in step_run
        assert "Skipping merge: PR updates workflow files" in step_run
        assert "gh pr view \"$PR_URL\" --json headRefOid --jq .headRefOid" in step_run
        assert 'if [ "$HEAD" != "$EXPECTED_SHA" ]' in step_run
        assert "skipping merge so newer CI can win" in step_run
        assert "gh pr merge --squash --delete-branch" in step_run
        assert "--auto" not in step_run
        assert "$GITHUB_SHA" not in step_run
        # Workflow-file skip and SHA guard must both precede merge.
        assert step_run.index(".github/workflows/") < step_run.index("gh pr merge")
        assert step_run.index("headRefOid") < step_run.index("gh pr merge")

    def test_template_ci_documents_opt_in_not_default(self):
        """Consumers opt in via thin CI; template must not enable by default."""
        text = (_TEMPLATES / "ci.yml").read_text(encoding="utf-8")
        assert "dependabot-auto-merge.yml@latest" in text
        assert "needs: [ci, semver]" in text
        assert "Merge Dependabot PR" in text
        assert "Allow auto-merge" not in text
        data = _load("ci.yml", templates=True)
        assert "dependabot-auto-merge" not in data["jobs"]

    def test_dogfood_check_opts_in(self):
        data = _load("check.yml")
        job = data["jobs"]["dependabot-auto-merge"]
        assert job["uses"] == "./.github/workflows/dependabot-auto-merge.yml"
        assert job["name"] == "Merge Dependabot PR"
        assert job["needs"] == ["ci", "semver"]
        assert "dependabot[bot]" in job["if"]
        assert job["permissions"]["contents"] == "write"
        assert job["permissions"]["pull-requests"] == "write"

    def test_howto_requires_needs_gate_last(self):
        """HOW-TO must require needs: so Dependabot merge runs last (thin + custom)."""
        howto = (_ROOT / "HOW-TO-USE.md").read_text(encoding="utf-8")
        assert "Gate so merge runs last" in howto
        assert "**must** declare `needs:`" in howto
        assert "needs: [ci, semver]" in howto
        assert "aggregate" in howto.lower()
        assert "SHA guard before merge" in howto
        assert "headRefOid" in howto
        template = (_TEMPLATES / "ci.yml").read_text(encoding="utf-8")
        assert "aggregate success job" in template
        reusable = (_WORKFLOWS / "dependabot-auto-merge.yml").read_text(encoding="utf-8")
        assert "aggregate" in reusable
        assert "headRefOid" in reusable
        assert "github.event.pull_request.head.sha" in reusable
        assert "ephemeral merge" in reusable
        assert "pull_request.head.sha" in howto
