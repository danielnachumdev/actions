"""Unit tests for scripts/ci/detect_layout.sh (no Actions runner required)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "ci" / "detect_layout.sh"
_ACTION_COPY = (
    _ROOT / ".github" / "actions" / "detect-layout" / "detect_layout.sh"
)


def _run(tmp: Path, env: dict[str, str]) -> dict[str, str]:
    out = tmp / "github_output"
    out.write_text("", encoding="utf-8")
    full_env = {
        **os.environ,
        "DETECT_OUTPUT_FILE": str(out),
        "EVENT_NAME": "pull_request",
        "ALLOW_EMPTY": "true",
        **env,
    }
    # Run with cwd = tmp so relative markers resolve.
    proc = subprocess.run(
        ["bash", str(_SCRIPT)],
        cwd=tmp,
        env=full_env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return _parse_output(out.read_text(encoding="utf-8"))


def _parse_output(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if "<<" in line:
            key, delim = line.split("<<", 1)
            buf: list[str] = []
            i += 1
            while i < len(lines) and lines[i] != delim:
                buf.append(lines[i])
                i += 1
            result[key] = "\n".join(buf)
            i += 1
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            result[k] = v
        i += 1
    return result


def test_action_copy_matches_scripts() -> None:
    assert _SCRIPT.read_text(encoding="utf-8") == _ACTION_COPY.read_text(
        encoding="utf-8"
    )


def test_python_and_github_yaml(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='x'\n\n[dependency-groups]\ndev = []\n",
        encoding="utf-8",
    )
    (tmp_path / ".github").mkdir()
    out = _run(tmp_path, {"ALLOW_EMPTY": "false"})
    assert out["run_python"] == "true"
    assert out["run_github_yaml"] == "true"
    assert out["run_node"] == "false"
    assert out["sync_args"] == "--group dev"


def test_sync_args_all_groups(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[dependency-groups]\ndev = []\nlint = []\n",
        encoding="utf-8",
    )
    out = _run(tmp_path, {})
    assert out["sync_args"] == "--all-groups"


def test_node_nvmrc_inference(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name":"x"}', encoding="utf-8")
    (tmp_path / ".nvmrc").write_text("22\n", encoding="utf-8")
    out = _run(tmp_path, {})
    assert out["run_node"] == "true"
    assert out["node_versions"] == '["22"]'


def test_terraform_validate_without_wif(tmp_path: Path) -> None:
    tf = tmp_path / "terraform"
    tf.mkdir()
    (tf / "versions.tf").write_text(
        'terraform { required_version = ">= 1.0" }\n', encoding="utf-8"
    )
    out = _run(tmp_path, {})
    assert out["run_terraform_validate"] == "true"
    assert out["run_terraform_apply"] == "false"


def test_terraform_apply_unlocked_by_wif(tmp_path: Path) -> None:
    tf = tmp_path / "terraform"
    tf.mkdir()
    (tf / "versions.tf").write_text(
        'terraform { required_version = ">= 1.0" }\n', encoding="utf-8"
    )
    out = _run(
        tmp_path,
        {
            "WORKLOAD_IDENTITY_PROVIDER": "projects/1/locations/global/workloadIdentityPools/p/providers/x",
            "SERVICE_ACCOUNT": "sa@example.iam.gserviceaccount.com",
        },
    )
    assert out["run_terraform_validate"] == "true"
    assert out["run_terraform_apply"] == "true"


def test_raft_requires_credentials(tmp_path: Path) -> None:
    raft = tmp_path / ".raft"
    raft.mkdir()
    (raft / "app.yaml").write_text("name: demo\n", encoding="utf-8")
    out = _run(tmp_path, {})
    assert out["run_raft"] == "false"
    out2 = _run(
        tmp_path,
        {
            "RAFT_SERVICE": "demo",
            "RAFT_GIT_REPO": "git@github.com:org/repo.git",
            "HAS_VPS_SSH_KEY": "true",
        },
    )
    assert out2["run_raft"] == "true"


def test_allow_empty_false_fails(tmp_path: Path) -> None:
    out_file = tmp_path / "out"
    proc = subprocess.run(
        ["bash", str(_SCRIPT)],
        cwd=tmp_path,
        env={
            **os.environ,
            "DETECT_OUTPUT_FILE": str(out_file),
            "EVENT_NAME": "pull_request",
            "ALLOW_EMPTY": "false",
        },
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0


def test_working_directory_scope(tmp_path: Path) -> None:
    pkg = tmp_path / "services" / "backend"
    pkg.mkdir(parents=True)
    (pkg / "pyproject.toml").write_text("[project]\nname='b'\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name":"root"}', encoding="utf-8")
    out = _run(tmp_path, {"WORKING_DIRECTORY": "services/backend"})
    assert out["run_python"] == "true"
    assert out["run_node"] == "false"
    assert out["working_directory"] == "services/backend"


@pytest.mark.parametrize("event", ["pull_request", "push"])
def test_skip_python_push(tmp_path: Path, event: str) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    out = _run(
        tmp_path,
        {"EVENT_NAME": event, "SKIP_PYTHON_PUSH": "true", "ALLOW_EMPTY": "true"},
    )
    if event == "push":
        assert out["run_python"] == "false"
    else:
        assert out["run_python"] == "true"
