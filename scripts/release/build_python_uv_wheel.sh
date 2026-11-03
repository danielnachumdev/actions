#!/usr/bin/env bash
# Stamp a semver into packaging files (ephemeral checkout) and build a wheel with uv.
#
# Usage:
#   build_python_uv_wheel.sh <vX.Y.Z> [out-dir] [distribution-name]
#
# distribution-name: PyPI/dist name used in the wheel filename (default: read
# from pyproject.toml project.name, with `-` → `_` fallbacks tried when locating
# the built artifact).
#
# Updates (first match each):
#   - pyproject.toml: version = "..."
#   - **/__init__.py: __version__ = "..." (first hit under project packages)
#   - publish.py: VERSION = "..." (if present)
set -euo pipefail

TAG="${1:?usage: build_python_uv_wheel.sh <vX.Y.Z> [out-dir] [distribution-name]}"
OUT_DIR="${2:-dist}"
DIST_NAME_INPUT="${3:-}"
ROOT="$(pwd)"
VERSION="${TAG#v}"

if [[ ! "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "build_python_uv_wheel.sh: expected tag vX.Y.Z, got ${TAG}" >&2
  exit 1
fi

python3 - "${VERSION}" <<'PY'
import pathlib
import re
import sys

version = sys.argv[1]


def replace_once(path: pathlib.Path, pattern: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    new, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise SystemExit(f"{path}: failed to update version ({count} matches for {pattern!r})")
    path.write_text(new, encoding="utf-8")


pyproject = pathlib.Path("pyproject.toml")
replace_once(pyproject, r'^version = "[^"]+"', f'version = "{version}"')

init_candidates = sorted(pathlib.Path(".").glob("*/__init__.py"))
init_candidates = [p for p in init_candidates if p.parts[0] not in {".venv", "tests", "build", "dist"}]
if init_candidates:
    for path in init_candidates:
        text = path.read_text(encoding="utf-8")
        if re.search(r'^__version__ = "', text, flags=re.M):
            replace_once(path, r'^__version__ = "[^"]+"', f'__version__ = "{version}"')
            break

publish = pathlib.Path("publish.py")
if publish.is_file() and re.search(r'^VERSION = "', publish.read_text(encoding="utf-8"), flags=re.M):
    replace_once(publish, r'^VERSION = "[^"]+"', f'VERSION = "{version}"')

print(f"stamped version → {version}")
PY

if [[ -z "${DIST_NAME_INPUT}" ]]; then
  DIST_NAME_INPUT="$(python3 - <<'PY'
import pathlib, re
text = pathlib.Path("pyproject.toml").read_text(encoding="utf-8")
m = re.search(r'^name = "([^"]+)"', text, re.M)
print(m.group(1) if m else "package")
PY
)"
fi

# Wheel filenames may use underscore or hyphen forms.
name_underscore="${DIST_NAME_INPUT//-/_}"
name_hyphen="${DIST_NAME_INPUT//_/-}"

mkdir -p "${OUT_DIR}"
rm -f "${OUT_DIR}/${name_underscore}-${VERSION}"-*.whl "${OUT_DIR}/${name_hyphen}-${VERSION}"-*.whl

echo "Building wheel for ${DIST_NAME_INPUT}==${VERSION}…"
uv build --wheel --out-dir "${OUT_DIR}"

WHEEL="$(ls -1 "${OUT_DIR}/${name_underscore}-${VERSION}"-*.whl "${OUT_DIR}/${name_hyphen}-${VERSION}"-*.whl 2>/dev/null | head -1 || true)"
[[ -n "${WHEEL}" && -f "${WHEEL}" ]] || {
  echo "build_python_uv_wheel.sh: no wheel for version ${VERSION} in ${OUT_DIR}" >&2
  ls -la "${OUT_DIR}" >&2 || true
  exit 1
}

printf 'wheel=%s\n' "${WHEEL}"
