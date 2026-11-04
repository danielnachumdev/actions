"""Unit tests for scripts/validate_skills.py (no skills-ref required)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "validate_skills.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("validate_skills", _SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vs():
    return _load_module()


def test_strip_removes_cursor_extensions_only(vs):
    content = """---
name: async
description: Offload work. Use when the user invokes /async.
disable-model-invocation: true
paths:
  - src/**
unknown-should-stay: true
---

# async
body
"""
    rebuilt, removed = vs.strip_cursor_extensions(content)
    assert removed == ["disable-model-invocation", "paths"]
    assert "disable-model-invocation" not in rebuilt
    assert "paths:" not in rebuilt
    assert "unknown-should-stay: true" in rebuilt
    assert "name: async" in rebuilt
    assert "# async\nbody" in rebuilt


def test_strip_requires_frontmatter(vs):
    with pytest.raises(ValueError, match="frontmatter"):
        vs.strip_cursor_extensions("# no frontmatter\n")


def test_discover_skill_dirs(vs, tmp_path: Path):
    (tmp_path / "keep").mkdir()
    (tmp_path / "keep" / "SKILL.md").write_text("---\nname: keep\n---\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "SKILL.md").write_text("---\nname: scripts\n---\n", encoding="utf-8")
    (tmp_path / "empty").mkdir()
    found = [p.name for p in vs.discover_skill_dirs(tmp_path)]
    assert found == ["keep"]


def test_resolve_root_prefers_argv(vs, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SKILLS_ROOT", str(tmp_path / "env"))
    (tmp_path / "env").mkdir()
    arg = tmp_path / "arg"
    arg.mkdir()
    assert vs.resolve_root(["validate_skills.py", str(arg)]) == arg.resolve()


def test_resolve_root_uses_env(vs, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "from-env"
    root.mkdir()
    monkeypatch.setenv("SKILLS_ROOT", str(root))
    monkeypatch.chdir(tmp_path)
    assert vs.resolve_root(["validate_skills.py"]) == root.resolve()
