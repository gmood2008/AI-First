from pathlib import Path

import pytest

from runtime.workflow.awe.capability_loader import CapabilityRef, VersionedCapabilityLoader


def _write_yaml(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_versioned_loader_can_load_two_versions_and_resolve_latest(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "cap1_v1.yaml",
        """
meta:
  id: demo.cap
  version: 1.0.0
interface: {inputs: {}, outputs: {}}
""",
    )
    _write_yaml(
        tmp_path / "cap1_v2.yaml",
        """
meta:
  id: demo.cap
  version: 2.0.0
interface: {inputs: {}, outputs: {}}
""",
    )

    loader = VersionedCapabilityLoader([tmp_path])
    loader.build_index()

    assert [str(v) for v in loader.index.list_versions("demo.cap")] == ["1.0.0", "2.0.0"]
    resolved = loader.resolve("demo.cap")
    assert str(resolved.version) == "2.0.0"

    resolved_1 = loader.resolve("demo.cap", "1.0.0")
    assert str(resolved_1.version) == "1.0.0"


def test_versioned_loader_dependency_discovery(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "a.yaml",
        """
meta:
  id: cap.a
  version: 1.0.0
  dependencies:
    - cap.b@^1.0.0
interface: {inputs: {}, outputs: {}}
""",
    )
    _write_yaml(
        tmp_path / "b.yaml",
        """
meta:
  id: cap.b
  version: 1.2.0
interface: {inputs: {}, outputs: {}}
""",
    )

    loader = VersionedCapabilityLoader([tmp_path])
    loader.build_index()

    ordered = loader.resolve_with_dependencies(CapabilityRef("cap.a"))
    assert [c.capability_id for c in ordered] == ["cap.b", "cap.a"]


def test_versioned_loader_detects_cycle(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "a.yaml",
        """
meta:
  id: cap.a
  version: 1.0.0
  dependencies:
    - cap.b
interface: {inputs: {}, outputs: {}}
""",
    )
    _write_yaml(
        tmp_path / "b.yaml",
        """
meta:
  id: cap.b
  version: 1.0.0
  dependencies:
    - cap.a
interface: {inputs: {}, outputs: {}}
""",
    )

    loader = VersionedCapabilityLoader([tmp_path])
    loader.build_index()

    with pytest.raises(RuntimeError, match="Dependency cycle"):
        loader.resolve_with_dependencies(CapabilityRef("cap.a"))
