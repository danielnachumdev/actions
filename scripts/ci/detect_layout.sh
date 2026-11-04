#!/usr/bin/env bash
# Portable layout detect for danielnachumdev/actions CI umbrella.
# Reads env knobs; writes GITHUB_OUTPUT keys (or DETECT_OUTPUT_FILE for tests).
set -euo pipefail

out_file="${DETECT_OUTPUT_FILE:-${GITHUB_OUTPUT:-}}"
if [[ -z "${out_file}" ]]; then
  echo "detect_layout: set GITHUB_OUTPUT or DETECT_OUTPUT_FILE" >&2
  exit 2
fi

root="${WORKING_DIRECTORY:-.}"
root="${root#./}"
[[ -z "${root}" ]] && root="."

repo_root="${REPO_ROOT:-.}"
repo_root="${repo_root#./}"
[[ -z "${repo_root}" ]] && repo_root="."

join_root() {
  local base="$1" rel="$2"
  if [[ "${base}" == "." ]]; then
    echo "${rel#./}"
  else
    echo "${base%/}/${rel#./}"
  fi
}

pyproject_path="$(join_root "${root}" "${PYPROJECT_PATH:-pyproject.toml}")"
package_json_path="$(join_root "${root}" "${PACKAGE_JSON_PATH:-package.json}")"
alembic_root_rel="${ALEMBIC_ROOT:-alembic}"
alembic_versions="$(join_root "${root}" "${alembic_root_rel}/versions")"
tf_root_rel="${TERRAFORM_WORKING_DIRECTORY:-terraform}"
tf_root="$(join_root "${root}" "${tf_root_rel}")"
raft_dir="$(join_root "${root}" ".raft")"
raft_manifest_rel="${RAFT_APP_MANIFEST:-.raft/app.yaml}"
raft_manifest="$(join_root "${root}" "${raft_manifest_rel}")"
github_dir="$(join_root "${repo_root}" ".github")"

event_name="${EVENT_NAME:-}"
if [[ "${event_name}" == "pull_request" ]]; then
  event_kind=pr
else
  event_kind=push
fi

pick() {
  # pick <shared> <push_override> — empty push override inherits shared.
  local shared="$1" push="$2"
  if [[ "${event_kind}" == "push" && -n "${push}" ]]; then
    echo "${push}"
  else
    echo "${shared}"
  fi
}

python_versions="$(pick "${PYTHON_VERSIONS:-["3.11","3.12","3.13"]}" "${PYTHON_VERSIONS_PUSH:-}")"
node_versions_push="${NODE_VERSIONS_PUSH:-}"
sync_args_push="${SYNC_ARGS_PUSH:-}"
pytest_command="${PYTEST_COMMAND:-pytest -q}"

infer_node_versions() {
  local pkg="$1"
  local nvmrc default='["20","22"]'
  nvmrc="$(join_root "${root}" ".nvmrc")"
  if [[ -f "${nvmrc}" ]]; then
    local ver
    ver="$(tr -d '[:space:]v' <"${nvmrc}" | head -n1 || true)"
    if [[ -n "${ver}" ]]; then
      echo "[\"${ver}\"]"
      return
    fi
  fi
  if [[ -f "${pkg}" ]] && command -v python3 >/dev/null 2>&1; then
    local engines
    engines="$(
      python3 - "${pkg}" <<'PY' || true
import json, re, sys
try:
    data = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
engines = (data.get("engines") or {}).get("node") or ""
m = re.search(r"(?:^|[\s=<>~^])(\d+)(?:\.|$)", str(engines))
if m:
    print(m.group(1))
PY
    )"
    if [[ -n "${engines}" ]]; then
      echo "[\"${engines}\"]"
      return
    fi
  fi
  echo "${default}"
}

# Empty NODE_VERSIONS → infer from .nvmrc / engines / default matrix.
if [[ -n "${NODE_VERSIONS:-}" ]]; then
  node_versions="$(pick "${NODE_VERSIONS}" "${node_versions_push}")"
else
  node_versions="$(pick "$(infer_node_versions "${package_json_path}")" "${node_versions_push}")"
fi

infer_sync_args() {
  local py="$1"
  if [[ ! -f "${py}" ]]; then
    echo "--group dev"
    return
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "--group dev"
    return
  fi
  python3 - "${py}" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
groups = []
m = re.search(r"(?ms)^\[dependency-groups\]\s*(.*?)(?=^\[|\Z)", text)
if m:
    groups = re.findall(r"(?m)^([A-Za-z0-9_-]+)\s*=", m.group(1))
if not groups:
    if re.search(r"(?m)^\[tool\.uv\.dev-dependencies\]", text) or re.search(
        r"(?m)^dev-dependencies\s*=", text
    ):
        print("--group dev")
        raise SystemExit
    print("")
    raise SystemExit
if groups == ["dev"]:
    print("--group dev")
elif len(groups) >= 1:
    print("--all-groups")
else:
    print("")
PY
}

# Empty SYNC_ARGS → infer from pyproject dependency groups.
if [[ -n "${SYNC_ARGS:-}" ]]; then
  sync_args="$(pick "${SYNC_ARGS}" "${sync_args_push}")"
else
  sync_args="$(pick "$(infer_sync_args "${pyproject_path}")" "${sync_args_push}")"
fi

if [[ "${event_kind}" == "push" ]]; then
  skip_python="${SKIP_PYTHON_PUSH:-false}"
  skip_node="${SKIP_NODE_PUSH:-false}"
else
  skip_python=false
  skip_node=false
fi

run_python=false
if [[ "${DISABLE_PYTHON:-false}" != "true" && "${skip_python}" != "true" && -f "${pyproject_path}" ]]; then
  run_python=true
fi

run_node=false
if [[ "${DISABLE_NODE:-false}" != "true" && "${skip_node}" != "true" && -f "${package_json_path}" ]]; then
  run_node=true
fi

run_github_yaml=false
if [[ "${DISABLE_GITHUB_YAML:-false}" != "true" && -d "${github_dir}" ]]; then
  run_github_yaml=true
fi

run_rebase_guard=false
if [[ "${DISABLE_REBASE_GUARD:-false}" != "true" && -d "${alembic_versions}" ]]; then
  run_rebase_guard=true
fi

has_tf=false
if [[ -d "${tf_root}" ]] && find "${tf_root}" -type f -name versions.tf -print -quit 2>/dev/null | grep -q .; then
  has_tf=true
else
  while IFS= read -r line; do
    p="${line#"${line%%[![:space:]]*}"}"
    p="${p%"${p##*[![:space:]]}"}"
    [[ -z "${p}" ]] && continue
    candidate="$(join_root "${root}" "${p}")"
    if [[ -f "${candidate}/versions.tf" ]]; then
      has_tf=true
      break
    fi
  done < <(echo "${EXTRA_TERRAFORM_MODULE_PATHS:-}" | tr ',' '\n')
fi

run_terraform_validate=false
run_terraform_apply=false
if [[ "${DISABLE_TERRAFORM:-false}" != "true" && "${has_tf}" == "true" ]]; then
  run_terraform_validate=true
  if [[ "${DISABLE_TERRAFORM_APPLY:-false}" != "true" \
    && -n "${WORKLOAD_IDENTITY_PROVIDER:-}" \
    && -n "${SERVICE_ACCOUNT:-}" ]]; then
    run_terraform_apply=true
  fi
fi

run_raft=false
raft_service="${RAFT_SERVICE:-}"
raft_git_repo="${RAFT_GIT_REPO:-}"
if [[ "${DISABLE_RAFT:-false}" != "true" && -d "${raft_dir}" ]]; then
  if [[ -f "${raft_manifest}" \
    && -n "${raft_service}" \
    && -n "${raft_git_repo}" \
    && "${HAS_VPS_SSH_KEY:-false}" == "true" ]]; then
    run_raft=true
  fi
fi

# Stack for allow-empty: CI-ish lanes (not rebase-only).
stack=false
if [[ "${run_python}" == "true" \
  || "${run_node}" == "true" \
  || "${run_github_yaml}" == "true" \
  || "${run_terraform_validate}" == "true" \
  || "${run_raft}" == "true" ]]; then
  stack=true
fi

{
  echo "working_directory=${root}"
  echo "run_python=${run_python}"
  echo "run_node=${run_node}"
  echo "run_github_yaml=${run_github_yaml}"
  echo "run_rebase_guard=${run_rebase_guard}"
  echo "run_terraform_validate=${run_terraform_validate}"
  echo "run_terraform_apply=${run_terraform_apply}"
  echo "run_raft=${run_raft}"
  echo "terraform_working_directory=${tf_root}"
  echo "alembic_root=$(join_root "${root}" "${alembic_root_rel}")"
  echo "raft_service=${raft_service}"
  echo "raft_git_repo=${raft_git_repo}"
  echo "python_versions=${python_versions}"
  echo "node_versions=${node_versions}"
  echo "sync_args<<EOF_SYNC"
  echo "${sync_args}"
  echo "EOF_SYNC"
  echo "pytest_command<<EOF_PYTEST_CMD"
  echo "${pytest_command}"
  echo "EOF_PYTEST_CMD"
} >>"${out_file}"

echo "detect: event=${event_name} kind=${event_kind} root=${root} repo_root=${repo_root}"
echo "detect: pyproject=${pyproject_path} package_json=${package_json_path}"
echo "detect: run_python=${run_python} run_node=${run_node} run_github_yaml=${run_github_yaml}"
echo "detect: run_rebase_guard=${run_rebase_guard} run_terraform_validate=${run_terraform_validate} run_terraform_apply=${run_terraform_apply} run_raft=${run_raft}"
echo "detect: python_versions=${python_versions} node_versions=${node_versions} sync_args=${sync_args}"

if [[ "${ALLOW_EMPTY:-false}" != "true" && "${stack}" != "true" ]]; then
  echo "detect: FAIL no CI lane selected (set allow-empty: true or add markers under working-directory)" >&2
  exit 1
fi
