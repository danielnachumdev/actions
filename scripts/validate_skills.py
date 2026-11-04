#!/usr/bin/env python3
"""Validate Agent Skills with skills-ref.

Cursor allows frontmatter extensions that the Agent Skills Spec (and
skills-ref) do not yet accept — notably ``disable-model-invocation``,
``paths``, ``icon``, and ``color``. Those keys stay in the real SKILL.md
files (Cursor behavior). For skills-ref we strip only that allowlist into a
temp copy, then validate so real spec errors still fail CI.

Install/run via ``scripts/validate_skills.sh`` (pinned skills-ref SHA).
Pass the skills tree root as argv[1] or ``SKILLS_ROOT`` (default: cwd).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import yaml

# Cursor-documented frontmatter extensions outside Agent Skills Spec.
# Do not add arbitrary keys here — unknown extras must still fail validation.
CURSOR_EXTENSION_FIELDS = frozenset(
    {
        "disable-model-invocation",
        "paths",
        "icon",
        "color",
    }
)

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".github",
        ".cursor",
        ".actions-standards",
        "scripts",
        "node_modules",
        ".venv",
        "venv",
        "tests",
        "templates",
        "examples",
    }
)


def resolve_root(argv: list[str]) -> Path:
    if len(argv) > 1 and argv[1].strip():
        return Path(argv[1]).expanduser().resolve()
    env = os.environ.get("SKILLS_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path.cwd().resolve()


def discover_skill_dirs(root: Path) -> list[Path]:
    skills: list[Path] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name in SKIP_DIR_NAMES:
            continue
        if (child / "SKILL.md").is_file():
            skills.append(child)
    return skills


def strip_cursor_extensions(content: str) -> tuple[str, list[str]]:
    if not content.startswith("---"):
        raise ValueError("SKILL.md must start with YAML frontmatter (---)")

    rest = content[3:]
    if rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\n"):
        rest = rest[1:]
    else:
        raise ValueError("SKILL.md must start with YAML frontmatter (---)")

    closer = None
    for marker in ("\n---\n", "\n---\r\n", "\n---"):
        idx = rest.find(marker)
        if idx != -1 and (closer is None or idx < closer[0]):
            closer = (idx, marker)
    if closer is None:
        raise ValueError("SKILL.md frontmatter not properly closed with ---")

    idx, marker = closer
    frontmatter_str = rest[:idx]
    body = rest[idx + len(marker) :]
    if marker == "\n---":
        body = ""

    data = yaml.safe_load(frontmatter_str)
    if not isinstance(data, dict):
        raise ValueError("SKILL.md frontmatter must be a YAML mapping")

    removed = sorted(k for k in CURSOR_EXTENSION_FIELDS if k in data)
    for key in removed:
        del data[key]

    dumped = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    rebuilt = f"---\n{dumped}---\n{body}"
    return rebuilt, removed


def validate_skill(skill_dir: Path) -> tuple[bool, str]:
    from skills_ref.validator import validate

    skill_md = skill_dir / "SKILL.md"
    try:
        original = skill_md.read_text(encoding="utf-8")
        stripped, removed = strip_cursor_extensions(original)
    except Exception as exc:  # noqa: BLE001 — surface parse errors as skill failures
        return False, f"FAIL  {skill_dir.name}: {exc}"

    with tempfile.TemporaryDirectory(prefix="validate-skills-") as tmp:
        # skills-ref checks directory name == frontmatter name
        tmp_skill = Path(tmp) / skill_dir.name
        tmp_skill.mkdir()
        (tmp_skill / "SKILL.md").write_text(stripped, encoding="utf-8")
        errors = validate(tmp_skill)

    if errors:
        detail = "; ".join(errors)
        return False, f"FAIL  {skill_dir.name}: {detail}"

    note = ""
    if removed:
        note = (
            " (stripped Cursor extensions for skills-ref: "
            f"{', '.join(removed)})"
        )
    return True, f"PASS  {skill_dir.name}{note}"


def append_step_summary(lines: list[str]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    with open(summary, "a", encoding="utf-8") as fh:
        fh.write("## Skills validation\n\n")
        for line in lines:
            fh.write(f"- {line}\n")
        fh.write("\n")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    root = resolve_root(argv)
    if not root.is_dir():
        msg = f"Skills root is not a directory: {root}"
        print(msg, file=sys.stderr)
        append_step_summary([f"FAIL  {msg}"])
        return 1

    skills = discover_skill_dirs(root)
    if not skills:
        msg = f"No skill directories with SKILL.md found under {root}"
        print(msg, file=sys.stderr)
        append_step_summary([f"FAIL  {msg}"])
        return 1

    print(f"Validating {len(skills)} skill(s) under {root}")
    print(
        "Note: Cursor extension fields "
        f"{sorted(CURSOR_EXTENSION_FIELDS)} are allowlisted "
        "(stripped only for skills-ref; kept in source)."
    )
    print()

    results: list[str] = []
    failed = 0
    for skill_dir in skills:
        ok, line = validate_skill(skill_dir)
        print(line)
        results.append(line)
        if not ok:
            failed += 1

    print()
    if failed:
        print(
            f"{failed}/{len(skills)} skill(s) failed validation.",
            file=sys.stderr,
        )
        append_step_summary(results)
        return 1

    print(f"All {len(skills)} skill(s) passed.")
    append_step_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
